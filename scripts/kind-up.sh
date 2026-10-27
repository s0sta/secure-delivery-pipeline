#!/usr/bin/env bash
# Local lab: a kind cluster with ingress-nginx, Kyverno and Argo CD, then the dev app via GitOps.
# Needs: docker, kind, kubectl, helm. Takes about 5 minutes.
set -euo pipefail
CLUSTER=${CLUSTER:-sdp}

kind create cluster --name "$CLUSTER" --wait 120s --config - <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration: { kubeletExtraArgs: { node-labels: "ingress-ready=true" } }
    extraPortMappings:
      - { containerPort: 80, hostPort: 8081, protocol: TCP }
  - role: worker
YAML

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
helm repo add kyverno https://kyverno.github.io/kyverno/ >/dev/null
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
helm repo update >/dev/null

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace \
  --set controller.hostPort.enabled=true --set controller.service.type=ClusterIP \
  --set-string controller.nodeSelector.ingress-ready=true --wait
helm upgrade --install kyverno kyverno/kyverno -n kyverno --create-namespace --wait
helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace --wait

kubectl apply -f deploy/policy/
kubectl apply -f deploy/argocd/project.yaml -f deploy/argocd/app-dev.yaml
echo "Argo CD admin password:"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
echo "UI: kubectl -n argocd port-forward svc/argocd-server 8443:443  →  https://localhost:8443"
