# ---- Builder Stage ----
    FROM golang:1.21-alpine AS builder
    # Or use the specific Go version from your README if needed, e.g., golang:1.18-alpine, but 1.21+ is recommended
    
    WORKDIR /app
    
    # Install build dependencies (git needed for go mod download)
    RUN apk add --no-cache git
    
    # Copy go.mod and go.sum first to leverage Docker cache
    COPY go.mod go.sum ./
    RUN go mod download
    
    # Copy the rest of the application source code
    COPY . .
    
    # Build the application statically linked (optional but good for alpine)
    # CGO_ENABLED=0 is important for static linking within Alpine
    # -ldflags "-s -w" strips debug symbols and info, reducing binary size
    RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /auth-api .
    
    # ---- Production Stage ----
    FROM alpine:latest
    
    # Install certificates needed for HTTPS calls (e.g., to Users API if it uses HTTPS)
    RUN apk --no-cache add ca-certificates
    
    WORKDIR /root/
    
    # Copy the built binary from the builder stage
    COPY --from=builder /auth-api .
    
    # Expose the port the app runs on (defined by AUTH_API_PORT env var)
    # You still need to set the ENV var in the K8s deployment
    EXPOSE 8000 
    
    # Command to run the executable
    # Environment variables (JWT_SECRET, AUTH_API_PORT, USERS_API_ADDRESS)
    # will be injected by Kubernetes via the Deployment manifest.
    CMD ["./auth-api"]