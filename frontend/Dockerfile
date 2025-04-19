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
    # Copy nginx config if you have a custom one
    # COPY nginx.conf /etc/nginx/conf.d/default.conf
    EXPOSE 80
    CMD ["nginx", "-g", "daemon off;"]