.PHONY: build run clean deps generate

# Generate Cap'n Proto code
generate:
	@export PATH=$$PATH:$$(go env GOPATH)/bin && \
	capnp compile -I$$(go list -f '{{.Dir}}' capnproto.org/go/capnp/v3/std) -ogo schema.capnp

# Install dependencies
deps:
	go mod download
	go mod tidy

# Build the project
build: generate deps
	go build -o bin/go-node .

# Run the node
run: build
	./bin/go-node

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f *_capnp.go

