# src/routes/dashboard.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Panel de control web"""
    # Obtener estadísticas
    stats = await get_statistics()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "title": "Ad Tracker Dashboard"
        }
    )