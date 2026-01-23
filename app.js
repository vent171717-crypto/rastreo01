// Variables globales
let currentData = {};
let deviceChart, locationChart, trendChart;

// Mostrar sección
function showSection(sectionId) {
    // Ocultar todas las secciones
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Mostrar sección seleccionada
    document.getElementById(sectionId).classList.add('active');
    
    // Actualizar menú activo
    document.querySelectorAll('.menu a').forEach(link => {
        link.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
}

// Cargar datos desde Google Ads
async function loadData() {
    const startDate = document.getElementById('startDate').value || '2024-01-01';
    const endDate = document.getElementById('endDate').value || '2024-01-31';
    
    try {
        const response = await axios.post('http://localhost:3000/api/devices-data', {
            customerId: localStorage.getItem('customerId'),
            startDate,
            endDate
        });
        
        if (response.data.success) {
            currentData = response.data.data;
            updateDashboard(currentData);
            updateCharts(currentData);
            updateTables(currentData);
        }
    } catch (error) {
        console.error('Error cargando datos:', error);
        alert('Error al cargar datos. Verifica la configuración.');
    }
}

// Actualizar dashboard
function updateDashboard(data) {
    const totalDevices = Object.values(data.devices).reduce((sum, device) => sum + device.requests, 0);
    const totalImpressions = Object.values(data.devices).reduce((sum, device) => sum + device.impressions, 0);
    
    document.getElementById('totalDevices').textContent = totalDevices.toLocaleString();
    document.getElementById('totalImpressions').textContent = totalImpressions.toLocaleString();
    document.getElementById('totalRequests').textContent = totalDevices.toLocaleString();
    
    // Dispositivos específicos
    document.getElementById('androidDevices').textContent = data.devices.android ? data.devices.android.requests.toLocaleString() : '0';
    document.getElementById('androidImpressions').textContent = data.devices.android ? data.devices.android.impressions.toLocaleString() : '0';
    document.getElementById('androidCTR').textContent = data.devices.android ? 
        ((data.devices.android.clicks / data.devices.android.impressions * 100) || 0).toFixed(2) + '%' : '0%';
    
    document.getElementById('iosDevices').textContent = data.devices.ios ? data.devices.ios.requests.toLocaleString() : '0';
    document.getElementById('iosImpressions').textContent = data.devices.ios ? data.devices.ios.impressions.toLocaleString() : '0';
    document.getElementById('iosCTR').textContent = data.devices.ios ? 
        ((data.devices.ios.clicks / data.devices.ios.impressions * 100) || 0).toFixed(2) + '%' : '0%';
}

// Crear/actualizar gráficos
function updateCharts(data) {
    // Gráfico de dispositivos
    const deviceCtx = document.getElementById('deviceChart').getContext('2d');
    
    if (deviceChart) {
        deviceChart.destroy();
    }
    
    deviceChart = new Chart(deviceCtx, {
        type: 'doughnut',
        data: {
            labels: ['Android', 'iOS', 'Desktop', 'Tablet'],
            datasets: [{
                data: [
                    data.devices.android?.impressions || 0,
                    data.devices.ios?.impressions || 0,
                    data.devices.desktop?.impressions || 0,
                    data.devices.tablet?.impressions || 0
                ],
                backgroundColor: [
                    '#4CAF50',
                    '#2196F3',
                    '#FF9800',
                    '#9C27B0'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Gráfico de ubicaciones
    const locationCtx = document.getElementById('locationChart').getContext('2d');
    
    if (locationChart) {
        locationChart.destroy();
    }
    
    // Datos de ejemplo para ubicaciones
    const locationData = {
        'España': 15000,
        'México': 12000,
        'Colombia': 8000,
        'Argentina': 7000,
        'Chile': 5000
    };
    
    locationChart = new Chart(locationCtx, {
        type: 'bar',
        data: {
            labels: Object.keys(locationData),
            datasets: [{
                label: 'Impresiones',
                data: Object.values(locationData),
                backgroundColor: '#4285f4'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Actualizar tabla de ubicaciones
function updateTables(data) {
    const tableBody = document.getElementById('locationData');
    tableBody.innerHTML = '';
    
    // Datos de ejemplo
    const sampleData = [
        { country: 'España', province: 'Madrid', city: 'Madrid', devices: 5000, impressions: 15000, requests: 7500 },
        { country: 'México', province: 'CDMX', city: 'Ciudad de México', devices: 4000, impressions: 12000, requests: 6000 },
        { country: 'Colombia', province: 'Bogotá', city: 'Bogotá', devices: 3000, impressions: 8000, requests: 4000 },
        { country: 'Argentina', province: 'Buenos Aires', city: 'Buenos Aires', devices: 2500, impressions: 7000, requests: 3500 },
        { country: 'Chile', province: 'Metropolitana', city: 'Santiago', devices: 2000, impressions: 5000, requests: 2500 }
    ];
    
    sampleData.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.country}</td>
            <td>${row.province}</td>
            <td>${row.city}</td>
            <td>${row.devices.toLocaleString()}</td>
            <td>${row.impressions.toLocaleString()}</td>
            <td>${row.requests.toLocaleString()}</td>
        `;
        tableBody.appendChild(tr);
    });
}

// Guardar configuración
function saveSettings() {
    const settings = {
        customerId: document.getElementById('customerId').value,
        developerToken: document.getElementById('developerToken').value,
        clientId: document.getElementById('clientId').value,
        clientSecret: document.getElementById('clientSecret').value,
        refreshToken: document.getElementById('refreshToken').value
    };
    
    localStorage.setItem('googleAdsSettings', JSON.stringify(settings));
    alert('Configuración guardada correctamente');
}

// Probar conexión
async function testConnection() {
    try {
        const settings = JSON.parse(localStorage.getItem('googleAdsSettings'));
        if (!settings) {
            alert('Primero guarda la configuración');
            return;
        }
        
        const response = await axios.post('http://localhost:3000/api/test-connection', settings);
        alert(response.data.message);
    } catch (error) {
        alert('Error de conexión: ' + error.message);
    }
}

// Filtro de ubicaciones
function filterLocations() {
    const country = document.getElementById('countryFilter').value;
    const region = document.getElementById('regionFilter').value;
    
    // Implementar lógica de filtrado aquí
    console.log('Filtrando por:', country, region);
}

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fechas por defecto
    const today = new Date().toISOString().split('T')[0];
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    const lastMonthStr = lastMonth.toISOString().split('T')[0];
    
    document.getElementById('startDate').value = lastMonthStr;
    document.getElementById('endDate').value = today;
    
    // Cargar configuración guardada
    const savedSettings = localStorage.getItem('googleAdsSettings');
    if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        document.getElementById('customerId').value = settings.customerId || '';
        document.getElementById('developerToken').value = settings.developerToken || '';
        document.getElementById('clientId').value = settings.clientId || '';
        document.getElementById('clientSecret').value = settings.clientSecret || '';
        document.getElementById('refreshToken').value = settings.refreshToken || '';
    }
    
    // Cargar datos iniciales
    loadData();
});