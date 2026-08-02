from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.cache.keys import CACHE_TTL_SECONDS, build_prefix
from app.cache.schemas import CacheFamilyOut, CacheInvalidateIn
from app.cache.service import invalidate_prefix
from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


@router.get("/families")
async def list_cache_families(
    request: Request,
    _actor: StaffUser = Depends(require_permission("cache.view")),
) -> DataResponse[list[CacheFamilyOut]]:
    return DataResponse(
        data=[
            CacheFamilyOut(family=family, ttl_seconds=ttl)
            for family, ttl in sorted(CACHE_TTL_SECONDS.items())
        ],
        meta=request_meta(request),
    )


@router.post("/invalidate")
async def invalidate_cache_family(
    payload: CacheInvalidateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("cache.invalidate")),
) -> DataResponse[dict[str, int]]:
    if payload.family not in CACHE_TTL_SECONDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown cache family.")
    removed = await invalidate_prefix(build_prefix(payload.family))
    return DataResponse(data={"keys_removed": removed}, meta=request_meta(request))
