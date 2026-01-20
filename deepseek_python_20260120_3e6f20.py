from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
from contextlib import asynccontextmanager
from src.tracker import AdRequestTracker
from src.database import init_db, get_db
from src.routes import ad_requests, devices, reports
import os

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Inicio
    logger.info("Iniciando Ad Tracker API")
    await init_db()
    
    # Configurar tracker global
    app.state.tracker = AdRequestTracker(
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    yield
    
    # Cierre
    logger.info("Cerrando Ad Tracker API")
    if hasattr(app.state, 'tracker'):
        await app.state.tracker.close()

# Crear aplicación FastAPI
app = FastAPI(
    title="Ad Request Tracker API",
    description="API para rastrear solicitudes de anuncios con Advertising ID",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware de seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # En producción especificar dominios
)

# Incluir routers
app.include_router(ad_requests.router, prefix="/api/v1", tags=["Ad Requests"])
app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "service": "Ad Request Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check para Koyeb/load balancers"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )