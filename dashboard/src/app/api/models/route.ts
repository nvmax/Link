import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const FALLBACK_MODELS: Record<string, string[]> = {
  lmstudio: [
    "gemma-4-e4b-it",
    "qwen2.5-7b-instruct",
    "qwen2.5-14b-instruct",
    "llama-3.1-8b-instruct",
    "mistral-7b-instruct"
  ],
  ollama: [
    "qwen2.5:7b",
    "qwen2.5:14b",
    "llama3.1:8b",
    "mistral",
    "gemma2:9b",
    "deepseek-r1:8b"
  ],
  openai: [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "o4-mini",
    "gpt-3.5-turbo"
  ],
  anthropic: [
    "claude-3-5-sonnet-20241022",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229"
  ],
  google: [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
  ],
  grok: [
    "grok-2-latest",
    "grok-beta",
    "grok-4.6"
  ],
  deepseek: [
    "deepseek-chat",
    "deepseek-reasoner"
  ],
  openrouter: [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.1-70b-instruct",
    "qwen/qwen-2.5-72b-instruct"
  ]
};

function getEnvApiKey(provider: string): string {
  try {
    const envPath = path.resolve(process.cwd(), '../.env');
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf8');
      const keyMap: Record<string, string> = {
        openai: 'OPENAI_API_KEY',
        google: 'GEMINI_API_KEY',
        anthropic: 'ANTHROPIC_API_KEY',
        grok: 'GROK_API_KEY',
        deepseek: 'DEEPSEEK_API_KEY',
        openrouter: 'OPENROUTER_API_KEY'
      };
      const envKey = keyMap[provider.toLowerCase()];
      if (envKey) {
        for (const line of content.split('\n')) {
          if (line.trim().startsWith(`${envKey}=`)) {
            return line.trim().split('=')[1]?.trim() || '';
          }
        }
      }
    }
  } catch (_) {}
  return '';
}

function getComfyUrl(): string {
  try {
    const envPath = path.resolve(process.cwd(), '../.env');
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf8');
      for (const line of content.split('\n')) {
        if (line.trim().startsWith('COMFY_URL=')) {
          return line.trim().split('=')[1]?.trim() || 'http://127.0.0.1:8188';
        }
      }
    }
  } catch (_) {}
  return 'http://127.0.0.1:8188';
}

export async function fetchLiveModelsInternal(
  providerName: string = 'LMStudio',
  baseUrl?: string,
  apiKey?: string
): Promise<{ success: boolean; live: boolean; models: string[]; provider: string; url?: string }> {
  const p = (providerName || 'LMStudio').trim();
  const pLower = p.toLowerCase();

  // 1. Try ComfyUI /yue2/models if available
  try {
    const comfyUrl = getComfyUrl();
    const query = new URLSearchParams({
      provider: p,
      base_url: baseUrl || '',
      api_key: apiKey || ''
    });
    const cRes = await fetch(`${comfyUrl}/yue2/models?${query.toString()}`, {
      signal: AbortSignal.timeout(1500)
    });
    if (cRes.ok) {
      const cData = await cRes.json();
      if (Array.isArray(cData.models) && cData.models.length > 0) {
        return {
          success: true,
          live: Boolean(cData.live),
          models: cData.models,
          provider: p,
          url: comfyUrl
        };
      }
    }
  } catch (_) {}

  // 2. Direct LM Studio queries
  if (pLower === 'lmstudio') {
    const candidateUrls: string[] = [];
    if (baseUrl && baseUrl.trim()) {
      candidateUrls.push(baseUrl.trim().replace(/\/+$/, ''));
    }
    const defaults = ['http://localhost:1234/v1', 'http://127.0.0.1:1234/v1'];
    for (const d of defaults) {
      if (!candidateUrls.includes(d)) candidateUrls.push(d);
    }

    for (const host of candidateUrls) {
      try {
        const endpoint = host.endsWith('/v1') ? `${host}/models` : `${host}/v1/models`;
        const res = await fetch(endpoint, {
          signal: AbortSignal.timeout(2500),
          headers: { 'Accept': 'application/json' }
        });
        if (res.ok) {
          const data = await res.json();
          const rawModels: string[] = (data?.data || [])
            .map((m: any) => m?.id)
            .filter(Boolean);

          if (rawModels.length > 0) {
            // Prioritize chat / text models over embedding models
            const chatModels = rawModels.filter(m => !m.toLowerCase().includes('embed'));
            const embedModels = rawModels.filter(m => m.toLowerCase().includes('embed'));
            return {
              success: true,
              live: true,
              models: [...chatModels, ...embedModels],
              provider: p,
              url: host
            };
          }
        }
      } catch (_) {}
    }
  }

  // 3. Direct Ollama queries
  if (pLower === 'ollama') {
    const ollamaUrl = (baseUrl || 'http://localhost:11434').trim().replace(/\/+$/, '');
    try {
      const res = await fetch(`${ollamaUrl}/api/tags`, {
        signal: AbortSignal.timeout(2500)
      });
      if (res.ok) {
        const data = await res.json();
        const models = (data?.models || []).map((m: any) => m?.name).filter(Boolean);
        if (models.length > 0) {
          return {
            success: true,
            live: true,
            models,
            provider: p,
            url: ollamaUrl
          };
        }
      }
    } catch (_) {}
    try {
      const res = await fetch(`${ollamaUrl}/v1/models`, {
        signal: AbortSignal.timeout(2000)
      });
      if (res.ok) {
        const data = await res.json();
        const models = (data?.data || []).map((m: any) => m?.id).filter(Boolean);
        if (models.length > 0) {
          return {
            success: true,
            live: true,
            models,
            provider: p,
            url: ollamaUrl
          };
        }
      }
    } catch (_) {}
  }

  // 4. OpenAI / OpenRouter queries if key available
  if (['openai', 'openrouter'].includes(pLower)) {
    const key = apiKey || getEnvApiKey(pLower);
    if (key) {
      const targetUrl = baseUrl || (pLower === 'openrouter' ? 'https://openrouter.ai/api/v1' : 'https://api.openai.com/v1');
      try {
        const res = await fetch(`${targetUrl.replace(/\/+$/, '')}/models`, {
          headers: { 'Authorization': `Bearer ${key}` },
          signal: AbortSignal.timeout(3000)
        });
        if (res.ok) {
          const data = await res.json();
          const models: string[] = (data?.data || []).map((m: any) => m?.id).filter(Boolean);
          if (models.length > 0) {
            let filtered = models;
            if (pLower === 'openai') {
              filtered = models.filter(m => ['gpt', 'o1', 'o3', 'o4'].some(k => m.toLowerCase().includes(k)));
            }
            return {
              success: true,
              live: true,
              models: filtered.length > 0 ? filtered : models,
              provider: p,
              url: targetUrl
            };
          }
        }
      } catch (_) {}
    }
  }

  // Fallback to provider predefined models
  const fallback = FALLBACK_MODELS[pLower] || FALLBACK_MODELS.lmstudio;
  return {
    success: false,
    live: false,
    models: [...fallback],
    provider: p
  };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const provider = searchParams.get('provider') || 'LMStudio';
  const baseUrl = searchParams.get('baseUrl') || searchParams.get('base_url') || undefined;
  const apiKey = searchParams.get('apiKey') || searchParams.get('api_key') || undefined;

  const result = await fetchLiveModelsInternal(provider, baseUrl, apiKey);
  return NextResponse.json(result);
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const provider = body.provider || 'LMStudio';
    const baseUrl = body.baseUrl || body.base_url || undefined;
    const apiKey = body.apiKey || body.api_key || undefined;

    const result = await fetchLiveModelsInternal(provider, baseUrl, apiKey);
    return NextResponse.json(result);
  } catch (err: any) {
    return NextResponse.json({
      success: false,
      live: false,
      models: FALLBACK_MODELS.lmstudio,
      error: err.message
    }, { status: 400 });
  }
}
