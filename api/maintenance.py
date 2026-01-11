from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from models.models import locations, location_days
from auth.auth import current_user

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post('/copy_prev_day')
async def copy_prev_day(day: Optional[str] = Query(None), force: Optional[bool] = Query(False), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    """Copy previous day's data to the given day for all locations.
    - `day`: YYYY-MM-DD, default today
    - `force`: if true, existing records for target day will be removed and recreated from previous day

    This endpoint is intended to be called from a cron job at day rollover.
    """
    # only superuser allowed
    if not getattr(user, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Только суперпользователь может запускать эту операцию")

    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # import helper
    from api.utils import ensure_location_day_from_prev

    # get all locations
    q = select(locations.c.id)
    r = await session.execute(q)
    locs = [row[0] for row in r.fetchall()]

    results = []
    for loc_id in locs:
        # if force, remove existing day first
        if force:
            qdel = delete(location_days).where(location_days.c.location_id == loc_id, location_days.c.day == req_day)
            await session.execute(qdel)
            await session.commit()

        new_id = await ensure_location_day_from_prev(session, loc_id, req_day)
        results.append({"location_id": loc_id, "created_day_id": new_id})

    return {"day": str(req_day), "results": results}
