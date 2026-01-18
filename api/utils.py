from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import warehouse_directors
from auth.db import User


async def is_hr(session: AsyncSession, user_id: int) -> bool:
    q = select(User).where(User.id == user_id)
    res = await session.execute(q)
    user = res.scalars().first()
    return user.is_hr if user else False


async def get_director_location(session: AsyncSession, user_id: int):
    q = select(warehouse_directors).where(warehouse_directors.c.user_id == user_id)
    r = await session.execute(q)
    return r.fetchone()


async def is_director_of_location(session: AsyncSession, user_id: int, location_id: int) -> bool:
    q = select(warehouse_directors).where(warehouse_directors.c.user_id == user_id, warehouse_directors.c.location_id == location_id)
    r = await session.execute(q)
    return r.fetchone() is not None


async def ensure_location_day_from_prev(session: AsyncSession, location_id: int, req_day) -> int:
    """Ensure there is a location_day for (location_id, req_day).
    If missing, try to copy from the most recent previous day (owners, stats, and employee assignments for owners assigned to this location).
    Returns new_or_existing_location_day_id or None if nothing to copy.
    """
    from sqlalchemy import select
    from models.models import location_days, location_day_owners, location_day_stats, employee_days

    # check existing
    q = select(location_days).where(location_days.c.location_id == location_id, location_days.c.day == req_day)
    r = await session.execute(q)
    ld = r.fetchone()
    if ld:
        return ld.id

    # find previous day for this location
    q2 = select(location_days).where(location_days.c.location_id == location_id, location_days.c.day < req_day).order_by(location_days.c.day.desc()).limit(1)
    r2 = await session.execute(q2)
    prev = r2.fetchone()
    if prev is None:
        return None

    # create new day
    res_ins = await session.execute(
        location_days.insert()
        .values(location_id=location_id, day=req_day, finalized=False)
        .returning(location_days.c.id)
    )
    new_day_id = res_ins.scalar_one()

    # copy owners
    q3 = select(location_day_owners.c.owner_id).where(location_day_owners.c.location_day_id == prev.id)
    r3 = await session.execute(q3)
    owners_list = [row.owner_id for row in r3.fetchall()]
    if owners_list:
        data = [{"location_day_id": new_day_id, "owner_id": oid} for oid in owners_list]
        await session.execute(location_day_owners.insert(), data)

    # copy stats if exists
    qstats = select(location_day_stats).where(location_day_stats.c.location_day_id == prev.id).order_by(location_day_stats.c.created_at.desc()).limit(1)
    rstats = await session.execute(qstats)
    stats = rstats.fetchone()
    if stats:
        # insert copied stats row
        vals = {}
        for col in ("arrived_actual", "expected", "outsourcing", "overtime", "lunch"):
            if hasattr(stats, col):
                vals[col] = getattr(stats, col)
        vals["location_day_id"] = new_day_id
        await session.execute(location_day_stats.insert().values(**vals))

    # copy employee_days for employees whose owner was assigned to this location on prev day
    if owners_list:
        qemp = select(employee_days.c.employee_id, employee_days.c.owner_id, employee_days.c.finalized).where(employee_days.c.day == prev.day, employee_days.c.owner_id.in_(owners_list))
        remp = await session.execute(qemp)
        rows = remp.fetchall()
        emp_data = []
        for r in rows:
            emp_id = r.employee_id
            owner_id = r.owner_id
            # avoid duplicates: ensure no record for emp_id and req_day
            qchk = select(employee_days).where(employee_days.c.employee_id == emp_id, employee_days.c.day == req_day)
            rchk = await session.execute(qchk)
            if rchk.fetchone() is None:
                emp_data.append({"employee_id": emp_id, "day": req_day, "owner_id": owner_id, "finalized": False})
        if emp_data:
            await session.execute(employee_days.insert(), emp_data)

    await session.commit()
    return new_day_id
