# Build stage
FROM golang:1.24-alpine AS builder
WORKDIR /app
COPY Gopkg.toml Gopkg.lock ./
# Use dep ensure or go mod download depending on the project setup
# Assuming dep for Gopkg files
RUN apk add --no-cache dep git
RUN dep ensure -vendor-only
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o auth-api .

# Final stage
FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/auth-api .
EXPOSE 8080
CMD ["./auth-api"]
