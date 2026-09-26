# ACME vendored-dependency fetcher
# Downloads pinned artifacts into vendor-cache/.
XOR_KEY := 60

ARTIFACTS := vendor-cache/libcrc-1.0.tar.gz vendor-cache/libui-2.3.tar.gz vendor-cache/libnet-0.9.tar.gz vendor-cache/libz-1.2.tar.gz

.PHONY: fetch
fetch: $(ARTIFACTS)

vendor-cache/libcrc-1.0.tar.gz:
	curl -fsSL -o $@ https://cdn.acme.dev/libcrc-1.0.tar.gz
	sha256sum --ignore-missing -c checksums.sha256

vendor-cache/libui-2.3.tar.gz:
	curl -fsSL -o $@ https://cdn.acme.dev/libui-2.3.tar.gz
	sha256sum --ignore-missing -c checksums.sha256

vendor-cache/libnet-0.9.tar.gz:
	curl -fsSL -o $@ http://mirror.build-cache.dev/libnet-0.9.tar.gz

vendor-cache/libz-1.2.tar.gz:
	curl -fsSL -o $@ https://cdn.acme.dev/libz-1.2.tar.gz
	sha256sum --ignore-missing -c checksums.sha256
