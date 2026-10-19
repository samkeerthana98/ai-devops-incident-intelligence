# GitOps Workflow with Argo CD

This document explains the GitOps workflow for deploying the AI DevOps Incident
Intelligence application to Kubernetes using Argo CD.

## Overview

The application is deployed via the Helm chart in `helm/ai-devops-incident-intelligence/`.
Argo CD watches the `main` branch of this repository and automatically syncs
the chart into the `ai-devops` namespace.

The Git repository is the single source of truth. Any change to the Helm chart
values or templates is picked up by Argo CD and applied to the cluster.

## Prerequisites

1. A running Kubernetes cluster.
2. Argo CD installed in the cluster (see the
   [Argo CD Getting Started guide](https://argo-cd.readthedocs.io/en/stable/getting_started/)).
3. This repository registered as an Argo CD repository:

   ```bash
   argocd repo add https://github.com/samkeerthana98/ai-devops-incident-intelligence.git
   ```

4. A container image pushed to a registry accessible from the cluster. Update
   `image.repository` and `image.tag` in `helm/ai-devops-incident-intelligence/values.yaml`
   or override via the Application manifest.

## Apply the Application Manifest

```bash
kubectl apply -f argocd/application.yaml
```

This creates an Argo CD `Application` resource that:

- Points to this Git repository's `main` branch.
- Deploys the Helm chart from `helm/ai-devops-incident-intelligence/`.
- Deploys into the `ai-devops` namespace (created automatically).
- Enables automated sync with prune and self-heal.

## Check Sync Status

```bash
# Application status
argocd app get ai-devops-incident-intelligence

# Sync status (short)
argocd app get ai-devops-incident-intelligence --show-params

# List resources managed by the application
argocd app resources ai-devops-incident-intelligence
```

Or via `kubectl`:

```bash
kubectl get application -n argocd ai-devops-incident-intelligence
```

## Check Health

```bash
# Pods in the deployed namespace
kubectl get pods -n ai-devops -l app.kubernetes.io/name=ai-devops-incident-intelligence

# Port-forward the service for local access
kubectl -n ai-devops port-forward svc/ai-devops-incident-intelligence 5000:80
```

The health check endpoint is available at `http://localhost:5000/health`.

## Sync Options

The Application manifest is configured with:

| Option | Description |
|--------|-------------|
| `automated.prune` | Removes resources that are no longer in Git. |
| `automated.selfHeal` | Re-syncs if someone makes manual changes in the cluster. |
| `CreateNamespace=true` | Creates the `ai-devops` namespace if it does not exist. |
| `ServerSideApply=true` | Uses server-side apply for safer conflict handling. |

## Update the Deployment

To change configuration:

1. Edit `helm/ai-devops-incident-intelligence/values.yaml` or the `helm.values`
   block in `argocd/application.yaml`.
2. Commit and push to `main`.
3. Argo CD detects the change and syncs automatically (self-heal).

To trigger a manual sync:

```bash
argocd app sync ai-devops-incident-intelligence
```

## Rollback

To roll back to a previous state, revert the Git commit and push. Argo CD will
sync the previous chart version automatically.

```bash
git revert <commit-sha>
git push origin main
```

## Cleanup

```bash
# Delete the application and all its resources
argocd app delete ai-devops-incident-intelligence

# Or via kubectl (the finalizer ensures cleanup)
kubectl delete -f argocd/application.yaml
```
