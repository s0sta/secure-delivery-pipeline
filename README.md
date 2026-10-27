# Secure delivery pipeline

[![ci](https://github.com/s0sta/secure-delivery-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/s0sta/secure-delivery-pipeline/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

A small Python API (`shop-api`) delivered the DevSecOps way: every change is tested and scanned, the image is
built once, **signed**, given an **SBOM** and **SLSA provenance**, deployed by **GitOps (Argo CD)**, and the cluster
**only runs images signed by this pipeline**.

The app is intentionally small. The value is the delivery system around it.

## What it shows

| Area | How |
|---|---|
| CI | GitHub Actions: ruff (incl. bandit rules), pytest with a 90 % coverage gate, container smoke test |
| Shift-left security | gitleaks (secrets), semgrep (SAST), Trivy (Dockerfile and Kubernetes misconfigurations), kubeconform |
| Supply chain | Trivy image scan, Syft SBOM (CycloneDX), cosign keyless signing, SBOM attestation, SLSA provenance |
| Delivery | Kustomize overlays (dev, prod), image pinned **by digest**, Argo CD auto-sync for dev, promotion PR for prod |
| Runtime security | Pod Security `restricted`, non-root, read-only FS, no capabilities, seccomp, default-deny NetworkPolicy |
| Admission control | Kyverno: verify the cosign signature; require limits and probes |
| Operations | Probes, HPA, PodDisruptionBudget, topology spread, Prometheus `/metrics`, runbook |

Details: [architecture](docs/architecture.md) · [security controls](docs/security-controls.md) · [runbook](docs/runbook.md)

## Pipeline

```
pull request:  test ─┬─ secrets ─┬─ build ─ smoke test ─ image scan ─ SBOM
                     ├─ sast ────┤
                     └─ iac ─────┘
main:          … the same … ─ push (digest) ─ cosign sign + attest ─ provenance ─ deploy dev (Git) ─ PR to prod
```

## Run it

```sh
make install test          # Python 3.12+
make run                   # http://127.0.0.1:8080/docs
docker compose up --build  # same, in a hardened container (read-only, no capabilities)
make kind-up               # local Kubernetes with ingress, Kyverno and Argo CD
```

API: `GET /health` · `GET /ready` · `GET /metrics` · `GET /api/v1/products` · `POST /api/v1/orders` ·
`GET /api/v1/orders` · `GET /api/v1/orders/{id}`

## Repository layout

```
app/                 FastAPI service (input validation, security headers, metrics)
tests/               pytest
Dockerfile           multi-stage, non-root, no pip in the runtime image
deploy/base          Deployment, Service, NetworkPolicy, PDB, HPA, ServiceAccount
deploy/overlays      dev (auto) and prod (via reviewed PR), each with its namespace
deploy/argocd        AppProject and Applications
deploy/policy        Kyverno policies (signed images, limits and probes)
.github/workflows    the pipeline
docs/                architecture, security controls, runbook
```

## Setup notes for a fork
- Settings → Actions → Workflow permissions: allow GitHub Actions to create pull requests (for the promotion PR).
- Create the environments `dev` (and optionally protection rules). If `main` is protected, let the bot push to
  `deploy/overlays/dev` or switch the dev step to a pull request as well.
- Change `s0sta/secure-delivery-pipeline` in `deploy/argocd/` and `deploy/policy/` to your repository.

---
Built by [Hosam Hani](https://s0sta.com) · MIT license
