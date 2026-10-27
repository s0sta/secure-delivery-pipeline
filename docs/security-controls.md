# Security controls

| # | Control | Tool / setting | Where | Fails the build? |
|---|---|---|---|---|
| 1 | Secrets never in Git | gitleaks (pre-commit + CI, full history) | `.pre-commit-config.yaml`, `secrets` job | yes |
| 2 | Secure code | ruff with bandit rules (`S`), semgrep `p/default` `p/python` | `test`, `sast` jobs | yes |
| 3 | Dependencies up to date | Dependabot (pip, Docker, Actions), pinned versions | `.github/dependabot.yml` | — |
| 4 | Secure Dockerfile | multi-stage, slim base, no pip in runtime, non-root UID 10001, healthcheck | `Dockerfile` | Trivy config |
| 5 | Secure manifests | Trivy config + kubeconform strict schema check | `iac` job | yes |
| 6 | No known critical CVEs | Trivy image scan (fixable CRITICAL) | `build` job | yes |
| 7 | Know what is inside | Syft SBOM (CycloneDX), attached to the image | `build` job | — |
| 8 | Prove who built it | cosign keyless signature + SLSA provenance | `build` job | — |
| 9 | Run only signed images | Kyverno `verifyImages` | `deploy/policy/verify-images.yaml` | admission |
| 10 | Least privilege pods | restricted PSA, non-root, read-only FS, drop ALL, seccomp, no SA token | `deploy/base/` | admission |
| 11 | Network isolation | default-deny + allow ingress/monitoring/DNS only | `deploy/base/networkpolicy.yaml` | — |
| 12 | Safe releases | prod only via reviewed PR; Argo CD self-heal; rollback = git revert | `promote-prod` job | review |
| 13 | Least privilege CI | `permissions:` per job, OIDC instead of stored keys | `.github/workflows/ci.yml` | — |
| 14 | App hardening | strict input validation (pydantic, `extra=forbid`), security headers, trusted hosts, no docs in prod | `app/main.py` | tests |

Mapped to the OWASP Top 10 CI/CD Security Risks: CICD-SEC-1 (flow control → reviewed promotion PR),
CICD-SEC-3 (dependency chain → Dependabot, SBOM), CICD-SEC-5 (PBAC → per-job permissions),
CICD-SEC-6 (credential hygiene → OIDC, gitleaks), CICD-SEC-9 (artifact integrity → cosign, provenance, Kyverno).
