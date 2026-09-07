.DEFAULT_GOAL := help

PACKAGE_ID    := lightning-control-center
PACKAGE_VERSION := $(shell node -p "require('./package.json').version" 2>/dev/null || echo "1.0.0")
TS_FILES      := $(shell find startos -name '*.ts')

.PHONY: help build clean install package inspect frontend

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

javascript/index.js: $(TS_FILES) tsconfig.json node_modules
	npx ncc build startos/index.ts -o javascript

# Copy frontend assets from repo root into startos-pkg/ for Docker build context
frontend:
	cp -r ../icons ./
	cp ../*.html ./
	cp ../lcc-theme.js ./

build: frontend javascript/index.js
	docker build \
		-f Dockerfile \
		-t $(PACKAGE_ID):$(PACKAGE_VERSION) \
		.

package: frontend javascript/index.js
	start-cli s9pk pack

install: package
	start-cli s9pk install $(PACKAGE_ID).s9pk

clean:
	rm -rf javascript node_modules $(PACKAGE_ID).s9pk icons *.html lcc-theme.js
