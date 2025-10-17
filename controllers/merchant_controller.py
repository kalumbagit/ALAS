
from fastapi import APIRouter



router = APIRouter(prefix="/merchants", tags=["Merchants - User Access"])
admin_router = APIRouter(prefix="/admin/manage/merchants", tags=["Merchants - Admin Access"])