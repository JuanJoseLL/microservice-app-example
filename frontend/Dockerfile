# ---- Build Stage ----
    FROM node:8-alpine AS build-stage

    WORKDIR /app
    
    # Install Python 2 and build tools needed by node-gyp (for node-sass)
    RUN apk add --no-cache python2 make g++
    
    COPY package*.json ./
    RUN npm install
    COPY . .
    RUN npm run build
    
    # ---- Production Stage ----
    FROM nginx:stable-alpine AS production-stage
    COPY --from=build-stage /app/dist /usr/share/nginx/html
    
    # Copy your custom Nginx config to overwrite the default
    # Assumes your custom file is named nginx.conf and is in the same directory as the Dockerfile
    COPY nginx.conf /etc/nginx/conf.d/default.conf
    
    # Expose the port Nginx will actually listen on
    EXPOSE 8080
    
    CMD ["nginx", "-g", "daemon off;"]