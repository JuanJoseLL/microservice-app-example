# ---- Build Stage ----
    FROM node:20-alpine AS build-stage
    # Or node:8-alpine if you want to strictly match the old version (EOL, not recommended)
    
    WORKDIR /app
    
    # Install Python and build tools needed by node-gyp (for node-sass)    
    COPY package*.json ./
    RUN npm install  # This should now find python3
    COPY . .
    RUN npm run build
    
    # ---- Production Stage ----
    FROM nginx:stable-alpine AS production-stage
    COPY --from=build-stage /app/dist /usr/share/nginx/html
    # Copy nginx config if you have a custom one
    # COPY nginx.conf /etc/nginx/conf.d/default.conf
    EXPOSE 80
    CMD ["nginx", "-g", "daemon off;"]