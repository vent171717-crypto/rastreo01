// Variables globales
let currentData = {};
let deviceChart, locationChart, trendChart;

// Determinar base API (usa mismo host/origen)
const API_BASE = window.location.origin;

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
    // Si la llamada viene con un evento inline, event puede estar disponible; si no, no hacemos nada extra
    try { event.currentTarget.classList.add('active'); } catch (e) {}
}

// Cargar datos desde Google Ads
async function loadData() {
    const startDate = document.getElementById('startDate').value || '2024-01-01';
    const endDate = document.getElementById('endDate').value || '2024-01-31';
    
    try {
        const response = await axios.post(`${API_BASE}/api/devices-data`, {
            customerId: localStorage.getItem('customerId'),
            startDate,
            endDate
        });
        
        if (response.data.success) {
            currentData = response.data.data;
            updateDashboard(currentData);
            updateCharts(currentData);
            updateTables(currentData);
        } else {
            console.error('Respuesta con success=false', response.data);
            alert('No se pudieron obtener datos: ' + (response.data.error || 'respuesta no exitosa'));
        }
    } catch (error) {
        console.error('Error cargando datos:', error);
        alert('Error al cargar datos. Verifica la configuración y que el backend esté activo.');
    }
}

// ... resto del app.js sin cambios en lógica, usando las mismas funciones que ya tenías ...
// (Puedes pegar aquí el resto de tu app.js tal cual, sólo cambiamos la base API al inicio)