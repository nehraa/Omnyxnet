.PHONY: build run clean deps generate

# Generate Cap'n Proto code
generate:
	@if [ -f "schema/schema.capnp.go" ]; then \
		echo "Cap'n Proto bindings already generated, skipping..."; \
	else \
		echo "Generating Cap'n Proto bindings..."; \
		cd schema && capnp compile -I$$(go env GOMODCACHE)/capnproto.org/go/capnp/v3@v3.1.0-alpha.2/std -ogo schema.capnp; \
	fi

# Install dependencies
deps:
	go mod download
	go mod tidy

# Build the project
build: deps generate
	go build -o bin/go-node .

# Run the node
run: build
	./bin/go-node

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f *_capnp.go

