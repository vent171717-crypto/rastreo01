// En tu SDK de anuncios
val advertisingId = AdvertisingIdClient.getAdvertisingIdInfo(context).id

// Recoger señales WiFi
val wifiManager = context.getSystemService(Context.WIFI_SERVICE) as WifiManager
val scanResults = wifiManager.scanResults

// Enviar a la API
val signals = mapOf(
    "advertising_id" to advertisingId,
    "wifi_access_points" to scanResults.map { 
        mapOf(
            "macAddress" to it.BSSID,
            "signalStrength" to it.level
        )
    }
)