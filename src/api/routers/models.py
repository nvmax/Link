from typing import Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import os
import aiohttp
import asyncio
import urllib.parse
import re
from src.core.config import Config
from src.core.logger import setup_logger
from src.core.model_extractor import extract_required_models
from src.api import state
from src.api.helpers import resolve_comfy_workspace
from src.core.cache import cache
from src.core import node_folder_cache

logger = setup_logger("api_models")

router = APIRouter()

# Global semaphore to limit concurrent HuggingFace search requests to avoid rate limits
hf_search_semaphore = asyncio.Semaphore(3)

@router.get("/api/models/progress")
async def get_download_progress() -> Dict[str, Any]:
    return state.active_downloads

@router.post("/api/models/check")
async def check_models(request: Request) -> Dict[str, Any]:
    try:
        workflow = await request.json()
        comfy_url = Config.COMFY_URL

        # Opportunistically refresh the node folder cache so that folder
        # Resolution uses ComfyUI's ground truth rather than heuristics.
        # We await this with a timeout so the cache is populated before we extract
        # required models, falling back gracefully if ComfyUI is slow or offline.
        if node_folder_cache.is_stale():
            try:
                await asyncio.wait_for(node_folder_cache.refresh(comfy_url), timeout=3.0)
            except Exception as e:
                logger.warning(f"Best-effort node folder cache refresh failed or timed out: {e}")

        missing = await _check_models_via_comfy_validation(workflow, comfy_url)
        if missing is not None:
            logger.info(f"Model check (ComfyUI validation): {len(missing)} missing")
            return {"required": missing, "missing": [m for m in missing if not m["installed"]]}

        raise HTTPException(
            status_code=503,
            detail="ComfyUI is unreachable. Please start ComfyUI before importing or checking workflows."
        )

    except Exception as e:
        logger.error(f"Model check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def _check_models_via_comfy_validation(workflow: dict, comfy_url: str) -> list[dict] | None:
    import uuid
    validation_client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": validation_client_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{comfy_url}/prompt",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()

        node_errors: dict = data.get("node_errors", {})
        prompt_id: str | None = data.get("prompt_id")

        if prompt_id and not node_errors:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{comfy_url}/queue",
                        json={"delete": [prompt_id]},
                        timeout=aiohttp.ClientTimeout(total=5)
                    )
                logger.info(f"Model check: all models present (queued {prompt_id} cancelled)")
            except Exception:
                pass
            return []

        missing_filenames: dict[str, dict] = {}
        extractor_map: dict[str, str] = {}
        for item in extract_required_models(workflow):
            extractor_map[item["filename"]] = item["folder"]

        for node_id, node_err in node_errors.items():
            node_class = node_err.get("class_type", "")
            for err in node_err.get("errors", []):
                if err.get("type") != "value_not_in_list":
                    continue
                extra = err.get("extra_info", {})
                field_name: str = extra.get("input_name", "")
                missing_file: str = extra.get("received_value", "")
                
                if not missing_file or not isinstance(missing_file, str):
                    continue

                # Priority 0: ComfyUI ground truth via object_info cache.
                # This is the folder the node itself declares — 100% accurate
                # when ComfyUI is online and the cache has been populated.
                folder = node_folder_cache.get_folder(node_class, field_name)

                # Priority 1: heuristic extractor map (built from workflow scan)
                if not folder:
                    folder = extractor_map.get(missing_file, "")

                # Priority 2: field-name semantics
                if not folder:
                    from src.core.model_extractor import _folder_from_field_name
                    folder = _folder_from_field_name(field_name) or "models"

                if folder:
                    logger.debug(
                        f"Resolved folder for '{missing_file}' "
                        f"({node_class}.{field_name}) → '{folder}'"
                    )
                missing_filenames[missing_file] = {
                    "folder": folder,
                    "filename": missing_file,
                    "installed": False,
                    "node_class": node_class,
                    "field": field_name,
                }

        all_required = extract_required_models(workflow)
        result = []
        seen_filenames: set[str] = set()

        for item in all_required:
            fname = item["filename"]
            if fname in seen_filenames:
                continue   # same file referenced by multiple nodes — already added
            seen_filenames.add(fname)
            if fname in missing_filenames:
                result.append(missing_filenames[fname])
            else:
                result.append({**item, "installed": True})

        for fname, info in missing_filenames.items():
            if fname not in seen_filenames:
                seen_filenames.add(fname)
                result.append(info)

        return result

    except aiohttp.ClientConnectorError:
        logger.warning("ComfyUI unreachable for model validation")
        return None
    except asyncio.TimeoutError:
        logger.warning("ComfyUI model validation timed out")
        return None
    except Exception as e:
        logger.warning(f"ComfyUI model validation failed: {e}")
        return None

@router.post("/api/models/search")
async def search_models(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
        filenames = body.get("filenames", [])
        
        results = {}
        preseeded_by_family = {
            "ltx": {"Comfy-Org/ltx-2", "Kijai/LTX2.3_comfy", "Lightricks/LTX-2.3", "Lightricks/LTX-2.3-fp8"},
            "flux": {"black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell", "Kijai/flux-fp8", "comfyanonymous/flux_flux8_repack"},
            "wan": {"Kijai/Wan2.1_comfy", "Comfy-Org/Wan2.1-ComfyUI", "comfyanonymous/wan2.1_repack"},
            "sd": {"stabilityai/stable-diffusion-3.5-large", "Comfy-Org/stable-diffusion-3.5-fp8", "stabilityai/stable-diffusion-xl-base-1.0", "runwayml/stable-diffusion-v1-5"}
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for filename in filenames:
                async def fetch_and_resolve_hf_repo():
                    exact_url = f"https://huggingface.co/api/search/full-text?q={urllib.parse.quote(filename)}&type=model"
                    found_repo = None
                    try:
                        async with session.get(exact_url, timeout=5) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                hits = data.get("hits", [])
                                if hits:
                                    hits.sort(key=lambda x: x.get("likes", 0), reverse=True)
                                    for hit in hits[:5]:
                                        repo_name = hit.get("name")
                                        if not repo_name: continue
                                        
                                        repo_api_url = f"https://huggingface.co/api/models/{repo_name}"
                                        try:
                                            async with session.get(repo_api_url, timeout=4) as resp_api:
                                                if resp_api.status == 200:
                                                    model_info = await resp_api.json()
                                                    siblings = model_info.get("siblings", [])
                                                    matches = [s.get("rfilename") for s in siblings if s.get("rfilename") == filename or s.get("rfilename", "").endswith(f"/{filename}")]
                                                    if matches:
                                                        found_repo = repo_name
                                                        break
                                        except Exception:
                                            pass
                                            
                                        # Fallback to direct check if API call fails
                                        if not found_repo:
                                            check_url = f"https://huggingface.co/{repo_name}/resolve/main/{filename}"
                                            try:
                                                async with session.head(check_url, timeout=3, allow_redirects=True) as check_resp:
                                                    if check_resp.status == 200:
                                                        found_repo = repo_name
                                                        break
                                            except Exception:
                                                pass
                            elif resp.status == 429:
                                logger.warning(f"Exact search hit HuggingFace 429 rate limit for {filename}")
                    except Exception as e:
                        logger.warning(f"Exact search HTTP error for {filename}: {e}")

                    if found_repo:
                        return found_repo

                    logger.info(f"Exact search failed or rate-limited for {filename}. Running relaxed dynamic HuggingFace search...")
                    stem = filename.rsplit('.', 1)[0]
                    tokens = re.split(r'[-_]', stem)
                    tokens = [t.strip() for t in tokens if t.strip()]
                    
                    queries = []
                    if len(tokens) >= 1:
                        queries.append(tokens[0])
                    if len(tokens) >= 2:
                        queries.append(f"{tokens[0]} {tokens[1]}")
                    if len(tokens) >= 3:
                        queries.append(f"{tokens[0]} {tokens[1]} {tokens[2]}")
                    queries.append(stem.replace('_', ' ').replace('-', ' '))
                    
                    filename_lower = filename.lower()
                    family = "other"
                    if "ltx" in filename_lower or "gemma" in filename_lower:
                        family = "ltx"
                    elif "flux" in filename_lower:
                        family = "flux"
                    elif "wan" in filename_lower:
                        family = "wan"
                    elif "stable-diffusion" in filename_lower or "sd" in filename_lower or "sdxl" in filename_lower:
                        family = "sd"
                    
                    family_repos = preseeded_by_family.get(family, set())
                    candidate_repos = set(family_repos)
                    keyword_repos = set()
                    
                    for q in queries:
                        q_quoted = urllib.parse.quote(q)
                        url_std = f"https://huggingface.co/api/models?search={q_quoted}&limit=40"
                        try:
                            async with session.get(url_std, timeout=5) as resp:
                                if resp.status == 200:
                                    repos = await resp.json()
                                    for r in repos:
                                        if isinstance(r, dict) and r.get("id"):
                                            candidate_repos.add(r.get("id"))
                                            keyword_repos.add(r.get("id"))
                                elif resp.status == 429:
                                    logger.warning(f"url_std hit HF 429 for query '{q}'")
                        except Exception as e:
                            logger.warning(f"url_std error: {e}")
                            
                        url_ft = f"https://huggingface.co/api/search/full-text?q={q_quoted}&type=model&limit=40"
                        try:
                            async with session.get(url_ft, timeout=5) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    hits = data.get("hits", [])
                                    for h in hits:
                                        if isinstance(h, dict) and h.get("name"):
                                            candidate_repos.add(h.get("name"))
                                            keyword_repos.add(h.get("name"))
                                elif resp.status == 429:
                                    logger.warning(f"url_ft hit HF 429 for query '{q}'")
                        except Exception as e:
                            logger.warning(f"url_ft error: {e}")

                    def get_repo_priority(repo_name):
                        score = 0
                        if repo_name in family_repos:
                            score += 100
                            
                        repo_lower = repo_name.lower()
                        if "comfy-org" in repo_lower:
                            score += 50
                        elif "kijai" in repo_lower:
                            score += 40
                        elif "comfy" in repo_lower:
                            score += 30
                        elif "lightricks" in repo_lower:
                            score += 20
                        elif "black-forest-labs" in repo_lower:
                            score += 20
                        elif "stabilityai" in repo_lower:
                            score += 20
                        
                        if repo_name in keyword_repos:
                            score += 15
                            
                        for t in tokens[:3]:
                            if t.lower() in repo_lower:
                                score += 3
                        return score

                    sorted_candidates = sorted(list(candidate_repos), key=get_repo_priority, reverse=True)
                    sem = asyncio.Semaphore(5)
                    
                    async def check_candidate(repo_id):
                        async with sem:
                            repo_api_url = f"https://huggingface.co/api/models/{repo_id}"
                            try:
                                async with session.get(repo_api_url, timeout=4) as resp:
                                    if resp.status == 200:
                                        model_info = await resp.json()
                                        siblings = model_info.get("siblings", [])
                                        matches = [s.get("rfilename") for s in siblings if s.get("rfilename") == filename or s.get("rfilename", "").endswith(f"/{filename}")]
                                        if matches:
                                            return repo_id
                            except Exception:
                                pass
                                
                            subpaths = [
                                f"{filename}",
                                f"diffusion_models/{filename}",
                                f"text_encoders/{filename}",
                                f"unet/{filename}",
                                f"vae/{filename}",
                                f"loras/{filename}"
                            ]
                            for subpath in subpaths:
                                check_url = f"https://huggingface.co/{repo_id}/resolve/main/{subpath}"
                                try:
                                    async with session.head(check_url, timeout=3, allow_redirects=True) as resp:
                                        if resp.status == 200:
                                            return repo_id
                                except Exception:
                                    pass
                            return None

                    tasks = [check_candidate(rid) for rid in sorted_candidates[:5]]
                    completed_results = await asyncio.gather(*tasks)
                    
                    for res in completed_results:
                        if res:
                            return res
                    return None

                async def fetch_with_semaphore():
                    async with hf_search_semaphore:
                        return await fetch_and_resolve_hf_repo()

                # Leverage CacheManager for search queries with 1-day (86400s) TTL
                resolved_repo = await cache.get_or_set(
                    f"hf_search_{filename}", 
                    fetch_with_semaphore, 
                    ttl=86400
                )
                results[filename] = resolved_repo

        return {"results": results}
    except Exception as e:
        logger.error(f"Search models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/models/download")
async def download_model(request: Request) -> Any:
    try:
        body = await request.json()
        folder   = body.get("folder")
        filename = body.get("filename")
        repo_id  = body.get("repo_id")
        hf_token = os.getenv("HF_TOKEN", "").strip()
        hf_path  = body.get("hf_path")

        if not folder or not filename:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: folder, filename"
            )

        url = ""
        headers: dict = {"User-Agent": "atlas-model-downloader/1.0"}

        if repo_id and repo_id.startswith("http"):
            url = repo_id
            if "huggingface.co" in url and "/blob/" in url:
                url = url.replace("/blob/", "/resolve/", 1)
        else:
            if not repo_id:
                raise HTTPException(status_code=400, detail="Missing repo_id or direct url")

            if not hf_path:
                try:
                    def get_repo_files():
                        from huggingface_hub import HfApi
                        return HfApi(token=hf_token).list_repo_files(repo_id=repo_id)
                    
                    files = await asyncio.to_thread(get_repo_files)
                    matches = [f for f in files if f == filename or f.endswith(f"/{filename}")]
                    if matches:
                        hf_path = matches[0]
                    else:
                        hf_path = filename
                except Exception as e:
                    logger.warning(f"Failed to list repo files for {repo_id}: {e}")
                    hf_path = filename

            url = f"https://huggingface.co/{repo_id}/resolve/main/{hf_path}"
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"

        comfy_workspace = resolve_comfy_workspace(Config.COMFY_PATH)
        dest_dir  = os.path.join(comfy_workspace, "models", folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)

        logger.info(f"Downloading model: {url} -> {dest_path}")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=3600),
                allow_redirects=True
            ) as resp:

                if resp.status == 401:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "status": "auth",
                            "detail": "HuggingFace authentication failed. Set your HF_TOKEN in Mission Control → Settings."
                        }
                    )

                if resp.status == 403:
                    repo_url = f"https://huggingface.co/{repo_id}"
                    return JSONResponse(
                        status_code=403,
                        content={"status": "gated", "repo_url": repo_url}
                    )

                if resp.status == 404:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "status": "not_found",
                            "detail": f"File not found on HuggingFace: {url}"
                        }
                    )

                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"HuggingFace returned HTTP {resp.status} for {url}"
                    )

                bytes_written = 0
                total_bytes = int(resp.headers.get("Content-Length", 0))
                
                state.active_downloads[filename] = {
                    "total": total_bytes,
                    "downloaded": 0,
                    "status": "downloading"
                }

                try:
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                            bytes_written += len(chunk)
                            state.active_downloads[filename]["downloaded"] = bytes_written
                    state.active_downloads[filename]["status"] = "done"
                except Exception as stream_err:
                    state.active_downloads[filename]["status"] = "error"
                    raise stream_err

        logger.info(f"Downloaded {filename} ({bytes_written / 1024 / 1024:.1f} MB) -> {dest_path}")
        return {"status": "success", "path": dest_path, "bytes": bytes_written}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
