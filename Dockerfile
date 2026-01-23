# Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copiar package.json e instalar dependencias
COPY backend/package*.json ./
RUN npm ci --only=production

# Copiar código del backend
COPY backend/ ./

# Copiar frontend
COPY public/ ./public/

# Exponer puerto
EXPOSE 3000

# Variables de entorno por defecto
ENV NODE_ENV=production
ENV PORT=3000

# Comando para iniciar
CMD ["node", "server.js"]
