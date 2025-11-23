.PHONY: build run clean deps generate

# Generate Cap'n Proto code
generate:
	@if [ -f "schema.capnp.go" ]; then \
		echo "Cap'n Proto bindings already generated, skipping..."; \
	else \
		echo "Generating Cap'n Proto bindings..."; \
		export PATH="$$(go env GOPATH)/bin:$$PATH" && \
		capnp compile -I/usr/include -I$$(go env GOMODCACHE)/capnproto.org/go/capnp/v3@v3.1.0-alpha.2/std -ogo schema/schema.capnp && \
		mv schema/schema.capnp.go .; \
	fi

# Install dependencies
deps:
	go mod download
	go mod tidy

# Build the project
build: deps generate
	mkdir -p bin
	CGO_LDFLAGS="-L$$(pwd)/../rust/target/release -lpangea_ces -Wl,-rpath,$$(pwd)/../rust/target/release" go build -o bin/go-node .

# Run the node
run: build
	./bin/go-node

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f *_capnp.go schema.capnp.go go-node

