import asyncio
import json
import sqlite3
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib
from dataclasses import dataclass, asdict
from aiohttp import web
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    """Estructura para información del dispositivo"""
    advertising_id: str  # GAID o AAID
    device_type: str  # 'android' o 'ios'
    ip_address: str
    user_agent: str
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None

@dataclass
class EnvironmentSignals:
    """Señales de entorno para geolocalización"""
    wifi_access_points: List[Dict] = None
    cell_towers: List[Dict] = None
    bluetooth_beacons: List[Dict] = None
    gps_coordinates: Optional[Dict] = None
    
    def __post_init__(self):
        if self.wifi_access_points is None:
            self.wifi_access_points = []
        if self.cell_towers is None:
            self.cell_towers = []
        if self.bluetooth_beacons is None:
            self.bluetooth_beacons = []

class AdRequestTracker:
    def __init__(self, db_path: str = "ad_requests.db", google_api_key: str = None):
        self.db_path = db_path
        self.google_api_key = google_api_key
        self._init_database()
        
    def _init_database(self):
        """Inicializa la base de datos SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla para solicitudes de anuncios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ad_requests (
                request_id TEXT PRIMARY KEY,
                advertising_id TEXT,
                device_type TEXT,
                ip_address TEXT,
                user_agent TEXT,
                device_model TEXT,
                os_version TEXT,
                app_id TEXT,
                sdk_version TEXT,
                request_timestamp DATETIME,
                response_status INTEGER,
                ad_type TEXT,
                country_code TEXT,
                estimated_lat REAL,
                estimated_lng REAL,
                accuracy_radius INTEGER,
                wifi_aps_count INTEGER,
                cell_towers_count INTEGER,
                is_vpn BOOLEAN DEFAULT 0
            )
        ''')
        
        # Tabla para históricos de ubicaciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                advertising_id TEXT,
                request_id TEXT,
                latitude REAL,
                longitude REAL,
                accuracy REAL,
                timestamp DATETIME,
                source TEXT,
                FOREIGN KEY (request_id) REFERENCES ad_requests(request_id)
            )
        ''')
        
        # Tabla para patrones de comportamiento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_patterns (
                advertising_id TEXT PRIMARY KEY,
                total_requests INTEGER DEFAULT 0,
                avg_requests_per_day REAL,
                common_countries TEXT,
                common_ip_prefixes TEXT,
                last_seen DATETIME,
                first_seen DATETIME
            )
        ''')
        
        # Índices para búsqueda rápida
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ad_id ON ad_requests(advertising_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON ad_requests(request_timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip ON ad_requests(ip_address)')
        
        conn.commit()
        conn.close()
    
    def _generate_request_id(self, device_info: DeviceInfo) -> str:
        """Genera un ID único para cada solicitud"""
        hash_string = f"{device_info.advertising_id}{device_info.ip_address}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    async def geolocate_with_signals(self, environment_signals: EnvironmentSignals) -> Optional[Dict]:
        """
        Utiliza la API de Geolocalización de Google con señales de entorno
        
        Documentación: https://developers.google.com/maps/documentation/geolocation/overview
        """
        if not self.google_api_key:
            logger.warning("No Google API key provided for geolocation")
            return None
        
        payload = {}
        
        # Construir payload basado en señales disponibles
        if environment_signals.wifi_access_points:
            payload["wifiAccessPoints"] = environment_signals.wifi_access_points[:20]  # Limitar a 20
        
        if environment_signals.cell_towers:
            payload["cellTowers"] = environment_signals.cell_towers[:20]
        
        if environment_signals.bluetooth_beacons:
            payload["bluetoothBeacons"] = environment_signals.bluetooth_beacons[:10]
        
        if not payload:
            logger.warning("No environment signals provided for geolocation")
            return None
        
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={self.google_api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Geolocation successful: {data.get('location')}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Geolocation API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Geolocation request failed: {e}")
            return None
    
    async def process_ad_request(self, device_info: DeviceInfo, 
                                environment_signals: EnvironmentSignals = None,
                                additional_data: Dict = None) -> Dict:
        """
        Procesa una solicitud de anuncio y registra toda la información
        """
        request_id = self._generate_request_id(device_info)
        timestamp = datetime.utcnow()
        
        # Datos de geolocalización
        geolocation_data = None
        if environment_signals and self.google_api_key:
            geolocation_data = await self.geolocate_with_signals(environment_signals)
        
        # Determinar país desde IP (simple)
        country_code = self._estimate_country_from_ip(device_info.ip_address)
        
        # Detectar posible VPN/Proxy
        is_vpn = self._detect_vpn_proxy(device_info.ip_address)
        
        # Extraer información adicional
        additional = additional_data or {}
        
        # Guardar en base de datos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ad_requests (
                request_id, advertising_id, device_type, ip_address, user_agent,
                device_model, os_version, app_id, sdk_version, request_timestamp,
                response_status, ad_type, country_code, estimated_lat, estimated_lng,
                accuracy_radius, wifi_aps_count, cell_towers_count, is_vpn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_id,
            device_info.advertising_id,
            device_info.device_type,
            device_info.ip_address,
            device_info.user_agent,
            device_info.device_model,
            device_info.os_version,
            additional.get('app_id'),
            additional.get('sdk_version'),
            timestamp,
            additional.get('response_status', 200),
            additional.get('ad_type', 'banner'),
            country_code,
            geolocation_data['location']['lat'] if geolocation_data else None,
            geolocation_data['location']['lng'] if geolocation_data else None,
            geolocation_data['accuracy'] if geolocation_data else None,
            len(environment_signals.wifi_access_points) if environment_signals else 0,
            len(environment_signals.cell_towers) if environment_signals else 0,
            is_vpn
        ))
        
        # Guardar historial de ubicación si hay datos
        if geolocation_data:
            cursor.execute('''
                INSERT INTO location_history 
                (advertising_id, request_id, latitude, longitude, accuracy, timestamp, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_info.advertising_id,
                request_id,
                geolocation_data['location']['lat'],
                geolocation_data['location']['lng'],
                geolocation_data['accuracy'],
                timestamp,
                'google_geolocation_api'
            ))
        
        # Actualizar patrones de comportamiento
        self._update_behavior_patterns(device_info.advertising_id, timestamp, country_code, device_info.ip_address)
        
        conn.commit()
        conn.close()
        
        return {
            "request_id": request_id,
            "timestamp": timestamp.isoformat(),
            "geolocation": geolocation_data,
            "country_code": country_code,
            "vpn_detected": is_vpn
        }
    
    def _estimate_country_from_ip(self, ip_address: str) -> str:
        """Estimación simple de país desde IP (para producción usar una base de datos IP)"""
        # Esta es una implementación simplificada
        # En producción, usar: maxmind, ip2location, o ipapi
        ip_parts = ip_address.split('.')
        if len(ip_parts) == 4:
            first_octet = int(ip_parts[0])
            if 1 <= first_octet <= 126:
                return "US"  # Ejemplo simplificado
            elif 128 <= first_octet <= 191:
                return "EU"
            elif 192 <= first_octet <= 223:
                return "ASIA"
        return "UNKNOWN"
    
    def _detect_vpn_proxy(self, ip_address: str) -> bool:
        """Detección básica de VPN/Proxy (simplificada)"""
        # Patrones comunes de IPs de datacenter/VPN
        datacenter_ranges = [
            ("192.0.2.0", "192.0.2.255"),  # TEST-NET
            ("198.18.0.0", "198.19.255.255"),  # Network benchmark
            ("100.64.0.0", "100.127.255.255"),  # Shared Address Space
        ]
        
        ip_num = self._ip_to_int(ip_address)
        for start, end in datacenter_ranges:
            if self._ip_to_int(start) <= ip_num <= self._ip_to_int(end):
                return True
        
        return False
    
    def _ip_to_int(self, ip: str) -> int:
        """Convierte IP a número entero"""
        parts = ip.split('.')
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
    
    def _update_behavior_patterns(self, advertising_id: str, timestamp: datetime, 
                                 country_code: str, ip_address: str):
        """Actualiza los patrones de comportamiento del dispositivo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM behavior_patterns WHERE advertising_id = ?', (advertising_id,))
        existing = cursor.fetchone()
        
        ip_prefix = '.'.join(ip_address.split('.')[:2])  # Primeros dos octetos
        
        if existing:
            # Actualizar registro existente
            total = existing[1] + 1
            avg_requests = total / ((timestamp - datetime.fromisoformat(existing[5])).days + 1)
            
            # Actualizar países comunes
            countries = set(existing[2].split(',')) if existing[2] else set()
            countries.add(country_code)
            
            # Actualizar prefijos IP comunes
            ip_prefixes = set(existing[3].split(',')) if existing[3] else set()
            ip_prefixes.add(ip_prefix)
            
            cursor.execute('''
                UPDATE behavior_patterns 
                SET total_requests = ?,
                    avg_requests_per_day = ?,
                    common_countries = ?,
                    common_ip_prefixes = ?,
                    last_seen = ?
                WHERE advertising_id = ?
            ''', (
                total,
                avg_requests,
                ','.join(countries),
                ','.join(ip_prefixes),
                timestamp,
                advertising_id
            ))
        else:
            # Nuevo dispositivo
            cursor.execute('''
                INSERT INTO behavior_patterns 
                (advertising_id, total_requests, avg_requests_per_day, 
                 common_countries, common_ip_prefixes, last_seen, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                advertising_id,
                1,
                1.0,
                country_code,
                ip_prefix,
                timestamp,
                timestamp
            ))
        
        conn.commit()
        conn.close()
    
    def get_device_history(self, advertising_id: str, limit: int = 100) -> List[Dict]:
        """Obtiene el historial de solicitudes de un dispositivo"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ad_requests 
            WHERE advertising_id = ? 
            ORDER BY request_timestamp DESC 
            LIMIT ?
        ''', (advertising_id, limit))
        
        requests = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return requests
    
    def find_similar_devices(self, ip_address: str = None, 
                            country_code: str = None,
                            device_model: str = None) -> List[Dict]:
        """Encuentra dispositivos similares basados en criterios"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT advertising_id, device_type, device_model, COUNT(*) as request_count FROM ad_requests WHERE 1=1"
        params = []
        
        if ip_address:
            query += " AND ip_address LIKE ?"
            params.append(f"{ip_address.split('.')[0]}.{ip_address.split('.')[1]}.%")
        
        if country_code:
            query += " AND country_code = ?"
            params.append(country_code)
        
        if device_model:
            query += " AND device_model = ?"
            params.append(device_model)
        
        query += " GROUP BY advertising_id ORDER BY request_count DESC LIMIT 50"
        
        cursor.execute(query, params)
        devices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return devices
    
    def generate_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Genera un reporte de actividad"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estadísticas básicas
        cursor.execute('''
            SELECT 
                COUNT(*) as total_requests,
                COUNT(DISTINCT advertising_id) as unique_devices,
                COUNT(DISTINCT ip_address) as unique_ips,
                AVG(accuracy_radius) as avg_accuracy
            FROM ad_requests 
            WHERE request_timestamp BETWEEN ? AND ?
        ''', (start_date, end_date))
        
        stats = cursor.fetchone()
        
        # Top países
        cursor.execute('''
            SELECT country_code, COUNT(*) as count
            FROM ad_requests 
            WHERE request_timestamp BETWEEN ? AND ?
            GROUP BY country_code 
            ORDER BY count DESC 
            LIMIT 10
        ''', (start_date, end_date))
        
        top_countries = cursor.fetchall()
        
        # Dispositivos más activos
        cursor.execute('''
            SELECT advertising_id, COUNT(*) as request_count
            FROM ad_requests 
            WHERE request_timestamp BETWEEN ? AND ?
            GROUP BY advertising_id 
            ORDER BY request_count DESC 
            LIMIT 10
        ''', (start_date, end_date))
        
        top_devices = cursor.fetchall()
        
        conn.close()
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "statistics": {
                "total_requests": stats[0],
                "unique_devices": stats[1],
                "unique_ips": stats[2],
                "average_accuracy_meters": round(stats[3] or 0, 2)
            },
            "top_countries": [{"country": c[0], "count": c[1]} for c in top_countries],
            "most_active_devices": [{"ad_id": d[0], "requests": d[1]} for d in top_devices]
        }

# API Web con FastAPI
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Ad Request Tracker API", 
              description="API para rastrear solicitudes de anuncios con Advertising ID y Geolocalización")

tracker = None

class AdRequestPayload(BaseModel):
    device_info: Dict
    environment_signals: Optional[Dict] = None
    additional_data: Optional[Dict] = None

class GeolocationRequest(BaseModel):
    wifi_access_points: Optional[List[Dict]] = None
    cell_towers: Optional[List[Dict]] = None
    bluetooth_beacons: Optional[List[Dict]] = None

@app.on_event("startup")
async def startup_event():
    """Inicializa el tracker al iniciar la aplicación"""
    global tracker
    # Configura tu API key de Google aquí
    google_api_key = "TU_API_KEY_AQUI"  # Reemplazar con tu API key
    tracker = AdRequestTracker(google_api_key=google_api_key)
    logger.info("Ad Request Tracker inicializado")

@app.post("/track-ad-request")
async def track_ad_request(payload: AdRequestPayload):
    """Endpoint para registrar una solicitud de anuncio"""
    try:
        device_info = DeviceInfo(**payload.device_info)
        
        env_signals = None
        if payload.environment_signals:
            env_signals = EnvironmentSignals(**payload.environment_signals)
        
        result = await tracker.process_ad_request(
            device_info, 
            env_signals, 
            payload.additional_data
        )
        
        return {
            "success": True,
            "request_id": result["request_id"],
            "geolocation_attempted": result["geolocation"] is not None
        }
    except Exception as e:
        logger.error(f"Error tracking ad request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/geolocate")
async def geolocate(request: GeolocationRequest):
    """Endpoint para geolocalización independiente"""
    try:
        env_signals = EnvironmentSignals(
            wifi_access_points=request.wifi_access_points,
            cell_towers=request.cell_towers,
            bluetooth_beacons=request.bluetooth_beacons
        )
        
        result = await tracker.geolocate_with_signals(env_signals)
        
        if result:
            return {
                "success": True,
                "location": result.get("location"),
                "accuracy": result.get("accuracy")
            }
        else:
            return {
                "success": False,
                "error": "Geolocation failed"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/device-history/{advertising_id}")
async def get_device_history(
    advertising_id: str,
    limit: int = Query(100, description="Número máximo de registros")
):
    """Obtiene el historial de un dispositivo específico"""
    try:
        history = tracker.get_device_history(advertising_id, limit)
        return {
            "advertising_id": advertising_id,
            "total_requests": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/find-similar")
async def find_similar_devices(
    ip_address: Optional[str] = None,
    country: Optional[str] = None,
    device_model: Optional[str] = None
):
    """Encuentra dispositivos similares"""
    try:
        devices = tracker.find_similar_devices(ip_address, country, device_model)
        return {
            "criteria": {
                "ip_address": ip_address,
                "country": country,
                "device_model": device_model
            },
            "found_devices": len(devices),
            "devices": devices
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report")
async def generate_report(
    days: int = Query(7, description="Número de días para el reporte")
):
    """Genera un reporte de actividad"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        report = tracker.generate_report(start_date, end_date)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint de salud de la API"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Ad Request Tracker API"
    }

# Script de ejemplo para simular solicitudes
async def simulate_ad_requests():
    """Simula solicitudes de anuncios para testing"""
    tracker = AdRequestTracker(google_api_key="TEST_KEY")
    
    # Dispositivo Android de ejemplo
    android_device = DeviceInfo(
        advertising_id="38400000-8cf0-11bd-b23e-10b96e40000d",  # GAID de ejemplo
        device_type="android",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Linux; Android 10; SM-G973F)",
        device_model="SM-G973F",
        os_version="Android 10",
        timestamp=datetime.utcnow().isoformat()
    )
    
    # Señales de entorno de ejemplo
    env_signals = EnvironmentSignals(
        wifi_access_points=[
            {
                "macAddress": "00:11:22:33:44:55",
                "signalStrength": -45,
                "age": 0
            }
        ],
        cell_towers=[
            {
                "cellId": 21532831,
                "locationAreaCode": 35632,
                "mobileCountryCode": 310,
                "mobileNetworkCode": 410,
                "signalStrength": -75,
                "age": 0
            }
        ]
    )
    
    # Procesar solicitud
    result = await tracker.process_ad_request(
        android_device,
        env_signals,
        {
            "app_id": "com.example.game",
            "sdk_version": "7.8.0",
            "ad_type": "interstitial"
        }
    )
    
    print(f"Solicitud procesada: {result['request_id']}")
    
    # Generar reporte
    report = tracker.generate_report()
    print(f"Reporte generado: {report['statistics']['total_requests']} solicitudes")

# Configuración y ejecución
if __name__ == "__main__":
    import uvicorn
    
    # Para ejecutar la API:
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # O para probar con simulación:
    # asyncio.run(simulate_ad_requests())
    
    print("""
    Instrucciones para usar la aplicación:
    
    1. Configura tu API Key de Google Cloud:
       - Ve a: https://console.cloud.google.com/apis/library/geolocation.googleapis.com
       - Habilita la API de Geolocalización
       - Crea una API Key y reemplaza "TU_API_KEY_AQUI" en el código
    
    2. Instala dependencias:
       pip install fastapi uvicorn aiohttp
    
    3. Ejecuta la API:
       uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
    4. Endpoints disponibles:
       - POST /track-ad-request    : Registrar solicitud de anuncio
       - POST /geolocate           : Geolocalización con señales
       - GET  /device-history/{id} : Historial de dispositivo
       - GET  /find-similar        : Buscar dispositivos similares
       - GET  /report              : Reporte de actividad
    
    5. Ejemplo de solicitud POST a /track-ad-request:
       {
         "device_info": {
           "advertising_id": "38400000-8cf0-11bd-b23e-10b96e40000d",
           "device_type": "android",
           "ip_address": "192.168.1.100",
           "user_agent": "Mozilla/5.0 (Linux; Android 10)",
           "device_model": "SM-G973F",
           "os_version": "Android 10"
         },
         "environment_signals": {
           "wifi_access_points": [
             {
               "macAddress": "00:11:22:33:44:55",
               "signalStrength": -45
             }
           ]
         },
         "additional_data": {
           "app_id": "com.example.app",
           "ad_type": "banner"
         }
       }
    """)