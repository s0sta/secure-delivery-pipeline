# Runbook

## Release to prod
1. Merge a change to `main`. Wait for the `ci` workflow to finish (dev is updated by itself).
2. Check dev: `kubectl -n shop-dev rollout status deploy/shop-api` and the Grafana dashboard.
3. Review and merge the pull request "Promote shop-api to prod". Argo CD syncs prod within 3 minutes.

## Roll back
- `git revert <promotion commit>` on `main` → Argo CD rolls back to the previous digest.
- Emergency (minutes count): `argocd app rollback shop-api-prod <id>`, then fix Git (self-heal is on).

## Check a running image
```sh
kubectl -n shop get deploy shop-api -o jsonpath='{.spec.template.spec.containers[0].image}'
cosign verify ghcr.io/s0sta/secure-delivery-pipeline@sha256:<digest> \
  --certificate-identity 'https://github.com/s0sta/secure-delivery-pipeline/.github/workflows/ci.yml@refs/heads/main' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
cosign verify-attestation --type cyclonedx ...same flags... ghcr.io/s0sta/secure-delivery-pipeline@sha256:<digest>
```

## A new CVE is published
1. `grype sbom:sbom.cdx.json` (or Trivy) on the SBOMs of the running digests.
2. Dependabot opens the update PR; CI rebuilds, scans, signs; promote as usual.

## A pod is rejected by Kyverno
`kubectl -n shop get events --field-selector reason=PolicyViolation` — usually an unsigned image or a manual
`kubectl set image`. Deploy only through Git.
