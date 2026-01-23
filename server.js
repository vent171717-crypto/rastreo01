// Agregar al inicio del server.js
const path = require('path');
const express = require('express');

const app = express();

// Servir archivos estáticos del frontend
app.use(express.static(path.join(__dirname, '../public')));

// Ruta principal
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Las otras rutas API permanecen igual...
