# from api.guest import router as guest_router
from api.auth import router as auth_router
from api.main_page import router as main_page_router
from api.admin import router as admin_router
from api.user import router as user_router
from api.owner import router as owner_router
from api.logs import router as logs_router
from api.files import router as files_router
from api.locations import router as locations_router
from api.employees import router as employees_router
from api.directors import router as directors_router
from api.hr import router as hr_router
from api.admin_panel import router as hr_admin_router
from fastapi import APIRouter


api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(user_router)
api_router.include_router(owner_router)
api_router.include_router(logs_router)
api_router.include_router(files_router)
api_router.include_router(locations_router)
api_router.include_router(employees_router)
api_router.include_router(directors_router)
api_router.include_router(hr_router)
api_router.include_router(hr_admin_router)
api_router.include_router(auth_router)
api_router.include_router(main_page_router)