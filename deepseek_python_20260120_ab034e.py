import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Base de datos
    DATABASE_PATH = os.getenv("DATABASE_PATH", "ad_requests.db")
    
    # Configuración de API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Límites
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_DEVICE_HISTORY = 1000
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "adtracker.log")