# Common tasks. Run `make help`.
IMAGE ?= shop-api:dev
.PHONY: help install lint test run image scan sbom k8s kind-up clean

help:            ## show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'
install:         ## create .venv and install dev tools
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
lint:            ## ruff lint (with bandit security rules) and format check
	.venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests
test:            ## unit tests with the 90 % coverage gate
	.venv/bin/pytest --cov=app --cov-report=term-missing
run:             ## run the API on http://127.0.0.1:8080 (docs at /docs)
	APP_ENV=dev .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
image:           ## build the container image
	docker build -t $(IMAGE) .
scan: image      ## scan the image and the repo with Trivy
	trivy image --severity HIGH,CRITICAL --ignore-unfixed $(IMAGE)
	trivy config --severity HIGH,CRITICAL .
sbom: image      ## make a CycloneDX SBOM with Syft
	syft $(IMAGE) -o cyclonedx-json=sbom.cdx.json
k8s:             ## render and validate the Kubernetes overlays
	for o in deploy/overlays/*/; do kustomize build $$o | kubeconform -strict -summary -ignore-missing-schemas; done
kind-up:         ## local cluster with ingress, Kyverno and Argo CD
	./scripts/kind-up.sh
clean:           ## remove caches and reports
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml sbom*.json *.sarif
