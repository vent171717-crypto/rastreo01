# Instalar Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Autenticarse
gcloud auth login

# Habilitar API de Geolocalización
gcloud services enable geolocation.googleapis.com

# Crear API Key
gcloud alpha services api-keys create --display-name="AdTrackerAPIKey"