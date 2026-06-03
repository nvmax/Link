from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timedelta
import os
import json
from sqlalchemy.orm import Session
from src.core.config import Config
from src.core.logger import setup_logger
from src.api import state
from src.database.session import SessionLocal, get_db
from src.database.models import ServerLimit, UserBan

logger = setup_logger("api_discord")

router = APIRouter()

@router.get("/api/discord/guild/{guild_id}")
async def get_guild(guild_id: int) -> Dict[str, Any]:
    if not state.bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    guild = state.bot_instance.get_guild(guild_id)
    if not guild:
        try:
            guild = await state.bot_instance.fetch_guild(guild_id)
        except Exception as e:
            logger.error(f"Failed to fetch guild {guild_id}: {e}")
            raise HTTPException(status_code=404, detail="Guild not found")
            
    return {
        "id": str(guild.id),
        "name": guild.name,
        "icon": str(guild.icon.url) if guild.icon else None
    }

@router.get("/api/discord/channel/{channel_id}")
async def get_channel(channel_id: int) -> Dict[str, Any]:
    if not state.bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    channel = state.bot_instance.get_channel(channel_id)
    if not channel:
        try:
            channel = await state.bot_instance.fetch_channel(channel_id)
        except Exception as e:
            logger.error(f"Failed to fetch channel {channel_id}: {e}")
            raise HTTPException(status_code=404, detail="Channel not found")
            
    return {
        "id": str(channel.id),
        "name": channel.name,
        "guild_name": channel.guild.name if hasattr(channel, 'guild') else "Unknown",
        "guild_id": str(channel.guild.id) if hasattr(channel, 'guild') else None
    }

@router.get("/api/discord/guilds")
async def get_discord_guilds() -> Dict[str, Any]:
    if not state.bot_instance:
        return {"guilds": [], "status": "offline"}
    
    if not state.bot_instance.is_ready():
        return {"guilds": [], "status": "loading"}
        
    try:
        guilds_data = []
        for guild in state.bot_instance.guilds:
            roles_data = []
            for role in guild.roles:
                color_str = f"#{role.color.value:06x}" if role.color.value != 0 else None
                roles_data.append({
                    "id": str(role.id),
                    "name": role.name,
                    "color": color_str,
                    "is_everyone": role.is_default(),
                    "position": role.position
                })
            
            roles_data.sort(key=lambda r: r["position"], reverse=True)
            
            guilds_data.append({
                "id": str(guild.id),
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else None,
                "roles": roles_data
            })
            
        return {"guilds": guilds_data, "status": "online"}
    except Exception as e:
        logger.error(f"Error fetching Discord guilds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/discord/permissions")
async def get_discord_permissions() -> Dict[str, Any]:
    permissions_path = os.path.join(Config.DATA_DIR, "permissions.json")
    if not os.path.exists(permissions_path):
        return {"guild_permissions": {}}
    try:
        with open(permissions_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading permissions.json: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read permissions: {str(e)}")

@router.post("/api/discord/permissions")
async def save_discord_permissions(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        permissions_path = os.path.join(Config.DATA_DIR, "permissions.json")
        os.makedirs(os.path.dirname(permissions_path), exist_ok=True)
        with open(permissions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# NEW ENDPOINTS FOR RATE LIMITS & USER BANS
# ==========================================

@router.get("/api/discord/guild/{guild_id}/members")
async def get_guild_members(guild_id: int) -> Dict[str, Any]:
    if not state.bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    guild = state.bot_instance.get_guild(guild_id)
    if not guild:
        try:
            guild = await state.bot_instance.fetch_guild(guild_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Guild not found in Discord client")

    members = []
    try:
        # Fetch top 100 members limit
        async for member in guild.fetch_members(limit=100):
            members.append({
                "id": str(member.id),
                "name": member.name,
                "display_name": member.display_name,
                "avatar": member.avatar.url if member.avatar else None
            })
    except Exception as fetch_err:
        logger.warning(f"Failed to fetch_members via API: {fetch_err}")
        # Fall back to guild.members cache
        for member in guild.members:
            members.append({
                "id": str(member.id),
                "name": member.name,
                "display_name": member.display_name,
                "avatar": member.avatar.url if member.avatar else None
            })
            
    return {"members": members}

@router.get("/api/discord/guild/{guild_id}/limits")
async def get_server_limits(guild_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    limits = db.query(ServerLimit).filter(ServerLimit.guild_id == guild_id).first()
    if not limits:
        # Return empty defaults
        return {
            "guild_id": guild_id,
            "rate_limit_per_minute": 0,
            "rate_limit_per_hour": 0,
            "quota_per_day": 0
        }
    return {
        "guild_id": limits.guild_id,
        "rate_limit_per_minute": limits.rate_limit_per_minute,
        "rate_limit_per_hour": limits.rate_limit_per_hour,
        "quota_per_day": limits.quota_per_day
    }

@router.post("/api/discord/guild/{guild_id}/limits")
async def save_server_limits(guild_id: str, request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        body = await request.json()
        rate_limit_per_minute = int(body.get("rate_limit_per_minute", 0))
        rate_limit_per_hour = int(body.get("rate_limit_per_hour", 0))
        quota_per_day = int(body.get("quota_per_day", 0))
        
        limits = db.query(ServerLimit).filter(ServerLimit.guild_id == guild_id).first()
        if not limits:
            limits = ServerLimit(guild_id=guild_id)
            db.add(limits)
        
        limits.rate_limit_per_minute = rate_limit_per_minute
        limits.rate_limit_per_hour = rate_limit_per_hour
        limits.quota_per_day = quota_per_day
        db.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving server limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/discord/guild/{guild_id}/bans")
async def get_user_bans(guild_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    from sqlalchemy import or_
    now = datetime.utcnow()
    # Fetch active and inactive bans
    bans = db.query(UserBan).filter(UserBan.guild_id == guild_id).all()
    
    results = []
    for ban in bans:
        # Check if active
        is_active = ban.expires_at is None or ban.expires_at > now
        time_left = None
        if is_active and ban.expires_at:
            diff = ban.expires_at - now
            time_left = int(diff.total_seconds())
            
        results.append({
            "id": ban.id,
            "user_id": ban.user_id,
            "username": ban.username,
            "banned_by": ban.banned_by,
            "reason": ban.reason,
            "ban_type": ban.ban_type,
            "duration_seconds": ban.duration_seconds,
            "created_at": ban.created_at.isoformat() if ban.created_at else None,
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "is_active": is_active,
            "time_left_seconds": time_left
        })
    return {"bans": results}

@router.post("/api/discord/guild/{guild_id}/bans")
async def create_user_ban(guild_id: str, request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        body = await request.json()
        user_id = str(body.get("user_id")).strip()
        username = str(body.get("username", "Unknown User")).strip()
        ban_type = str(body.get("ban_type", "ban")).strip() # "ban" or "restrict"
        duration_seconds = body.get("duration_seconds") # int or None
        reason = str(body.get("reason", "")).strip()
        banned_by = str(body.get("banned_by", "Admin")).strip()

        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")

        if duration_seconds is not None:
            duration_seconds = int(duration_seconds)
            expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
        else:
            expires_at = None

        # Delete any existing active ban for the user first to overwrite
        db.query(UserBan).filter(
            UserBan.guild_id == guild_id,
            UserBan.user_id == user_id
        ).delete()

        new_ban = UserBan(
            guild_id=guild_id,
            user_id=user_id,
            username=username,
            ban_type=ban_type,
            duration_seconds=duration_seconds,
            reason=reason,
            banned_by=banned_by,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        db.add(new_ban)
        db.commit()
        return {"status": "success", "id": new_ban.id}
    except Exception as e:
        logger.error(f"Error creating user ban: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/discord/guild/{guild_id}/bans/{user_id}")
async def lift_user_ban(guild_id: str, user_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        # Delete or expire the ban
        bans_deleted = db.query(UserBan).filter(
            UserBan.guild_id == guild_id,
            UserBan.user_id == user_id
        ).delete()
        
        db.commit()
        if bans_deleted == 0:
            raise HTTPException(status_code=404, detail="No active ban found for this user.")
        return {"status": "success", "message": f"Ban lifted for user {user_id}."}
    except Exception as e:
        logger.error(f"Error lifting user ban: {e}")
        raise HTTPException(status_code=500, detail=str(e))
