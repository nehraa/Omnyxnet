FROM rust:1.84-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    musl-dev \
    pkg-config \
    openssl-dev

# Copy manifest files
COPY Cargo.toml Cargo.lock ./

# Copy source
COPY src ./src

# Build in release mode
RUN cargo build --release

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/target/release/pangea-rust-compute .

# Expose RPC port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD nc -z localhost 9090 || exit 1

CMD ["./pangea-rust-compute", "--listen", "0.0.0.0:9090"]
