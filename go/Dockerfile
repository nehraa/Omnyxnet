# Multi-stage build for Go node
FROM golang:1.25-alpine AS builder

# Install dependencies
RUN apk add --no-cache \
    build-base \
    capnproto \
    capnproto-dev \
    git

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Generate Cap'n Proto code
RUN capnp compile -ogo schema/schema.capnp

# Build the application
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o go-node .

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates capnproto

WORKDIR /root/

# Copy the binary
COPY --from=builder /app/go-node .

# Expose ports
EXPOSE 8080 9090

# Command to run
CMD ["./go-node"]