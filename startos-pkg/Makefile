.DEFAULT_GOAL := help

PACKAGE_ID    := lightning-control-center
PACKAGE_VERSION := $(shell node -p "require('./package.json').version" 2>/dev/null || echo "1.0.0")
TS_FILES      := $(shell find startos -name '*.ts')

.PHONY: help build clean install package inspect

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build    Compile TypeScript and build Docker image"
	@echo "  package  Build .s9pk package"
	@echo "  install  Install package to a connected Start9 server"
	@echo "  clean    Remove build artifacts"

node_modules: package.json
	npm install

dist/main.js: $(TS_FILES) tsconfig.json node_modules
	npx tsc

build: dist/main.js
	docker build \
		-f Dockerfile \
		-t $(PACKAGE_ID):$(PACKAGE_VERSION) \
		..

package: build
	start-cli s9pk pack

install: package
	start-cli s9pk install $(PACKAGE_ID).s9pk

clean:
	rm -rf dist node_modules $(PACKAGE_ID).s9pk
