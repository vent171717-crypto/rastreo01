import AdSupport
import CoreLocation

let advertisingId = ASIdentifierManager.shared().advertisingIdentifier.uuidString

// Usar CLLocationManager para señales
let locationManager = CLLocationManager()
// Configurar y recoger datos de entorno