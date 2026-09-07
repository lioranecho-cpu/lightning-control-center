ARCHES := x86 arm

FRONTEND_SOURCES := $(wildcard ../icons/*) $(wildcard ../*.html) ../lcc-theme.js

.frontend-stamp: $(FRONTEND_SOURCES)
	cp -r ../icons ./
	cp ../*.html ./
	cp ../lcc-theme.js ./
	@touch $@

frontend: .frontend-stamp

include node_modules/@start9labs/start-sdk/s9pk.mk

# Add frontend as prerequisite to the specific s9pk output files (non-pattern, so it merges)
$(PACKAGE_ID)_x86_64.s9pk $(PACKAGE_ID)_aarch64.s9pk $(PACKAGE_ID).s9pk: .frontend-stamp
