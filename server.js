const express = require('express');
const cors = require('cors');
require('dotenv').config();
const path = require('path');
const { GoogleAdsApi } = require('google-ads-api');

const app = express();
app.use(cors());
app.use(express.json());

// Servir archivos estáticos desde /public
app.use(express.static(path.join(__dirname, 'public')));

// Configuración Google Ads API
const client = new GoogleAdsApi({
  client_id: process.env.GOOGLE_CLIENT_ID,
  client_secret: process.env.GOOGLE_CLIENT_SECRET,
  developer_token: process.env.DEVELOPER_TOKEN,
});

// Endpoint para obtener datos de dispositivos
app.post('/api/devices-data', async (req, res) => {
  try {
    const { customerId, startDate, endDate } = req.body;
    
    const customer = client.Customer({
      customer_id: customerId,
      refresh_token: process.env.REFRESH_TOKEN,
    });

    // Consulta para métricas de dispositivos
    const query = `
      SELECT
        segments.device AS device_type,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        geographic_view.country_criterion_id,
        geographic_view.location_type
      FROM geographic_view
      WHERE segments.date BETWEEN '${startDate}' AND '${endDate}'
      AND geographic_view.location_type IN ('COUNTRY', 'PROVINCE', 'CITY')
      ORDER BY metrics.impressions DESC
    `;

    const results = await customer.query(query);
    
    // Procesar datos
    const processedData = processGoogleAdsData(results);
    
    res.json({
      success: true,
      data: processedData,
      summary: generateSummary ? generateSummary(processedData) : {}
    });
    
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// Endpoint para datos por ubicación
app.post('/api/location-data', async (req, res) => {
  try {
    const { customerId, locationType } = req.body;
    
    const customer = client.Customer({
      customer_id: customerId,
      refresh_token: process.env.REFRESH_TOKEN,
    });

    const query = `
      SELECT
        geographic_view.country_criterion_id,
        geographic_view.province_criterion_id,
        geographic_view.city_criterion_id,
        metrics.impressions,
        metrics.clicks,
        metrics.average_cpc,
        segments.device
      FROM geographic_view
      WHERE geographic_view.location_type = '${locationType}'
      AND segments.date >= '2024-01-01'
      LIMIT 100
    `;

    const results = await customer.query(query);
    
    res.json({
      success: true,
      data: results,
      map: typeof generateLocationMap === 'function' ? generateLocationMap(results) : {}
    });
    
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
});

// Procesar datos de Google Ads (igual que antes)
function processGoogleAdsData(data) {
  const devices = {
    android: { impressions: 0, clicks: 0, requests: 0 },
    ios: { impressions: 0, clicks: 0, requests: 0 },
    desktop: { impressions: 0, clicks: 0, requests: 0 },
    tablet: { impressions: 0, clicks: 0, requests: 0 }
  };
  
  const locations = {
    countries: {},
    provinces: {},
    cities: {}
  };
  
  data.forEach(row => {
    // Por dispositivo (row.segments.device puede ser 'ANDROID', 'IOS' u otro)
    const deviceRaw = row.segments && row.segments.device ? String(row.segments.device).toLowerCase() : null;
    let deviceKey = null;
    if (deviceRaw) {
      if (deviceRaw.includes('android')) deviceKey = 'android';
      else if (deviceRaw.includes('ios') || deviceRaw.includes('iphone') || deviceRaw.includes('ipad')) deviceKey = 'ios';
      else if (deviceRaw.includes('desktop')) deviceKey = 'desktop';
      else if (deviceRaw.includes('tablet')) deviceKey = 'tablet';
    }
    if (deviceKey && row.metrics) {
      const impressions = parseInt(row.metrics.impressions || 0, 10);
      const clicks = parseInt(row.metrics.clicks || 0, 10);
      devices[deviceKey].impressions += impressions;
      devices[deviceKey].clicks += clicks;
      devices[deviceKey].requests += Math.floor(impressions * 0.8); // Estimación
    }
    
    // Por ubicación: placeholder para extender
    if (row.geographic_view) {
      // se puede mapear geographic_view.country_criterion_id a nombres con la API de recursos si es necesario
    }
  });
  
  return { devices, locations };
}

// Si hay un build SPA, devolver index.html para rutas no-API
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor ejecutándose en puerto ${PORT}`);
});