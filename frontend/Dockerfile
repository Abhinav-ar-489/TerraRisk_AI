# ==============================================================================
# TerraRisk AI - Frontend Production Container
# Multi-stage Docker build: Vite compile + Nginx Alpine
# ==============================================================================

# Build Stage
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# Build production SPA bundle
RUN npm run build

# Runtime Stage
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Copy production build from builder stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
