# STIX Enterprise Deployment Guide

This guide provides comprehensive instructions for deploying STIX (Shield Trust and Integrity eXecution) in enterprise production environments.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [Deployment Options](#deployment-options)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Security Configuration](#security-configuration)
7. [High Availability](#high-availability)
8. [Monitoring & Observability](#monitoring--observability)
9. [Backup & Recovery](#backup--recovery)
10. [Scaling Guidelines](#scaling-guidelines)
11. [Compliance Considerations](#compliance-considerations)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

STIX consists of five backend services plus the dashboard:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Load Balancer / Ingress                        │
└─────────────────────────────────────────────────────────────────────────┘
                    │               │               │
                    ▼               ▼               ▼
        ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
        │   Enforcer    │  │   Evidence    │  │   Approvals   │
        │   (Policy     │  │   (Audit      │  │   (Workflow   │
        │   Decisions)  │  │   Trail)      │  │   Engine)     │
        └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
            ┌───────────────┐              ┌───────────────┐
            │  PostgreSQL   │              │    Redis      │
            │  (Primary DB) │              │   (Cache)     │
            └───────────────┘              └───────────────┘
```

### Service Descriptions

| Service | Purpose | Port | Critical Level |
|---------|---------|------|----------------|
| **Enforcer** | Policy evaluation, authorization decisions | 3001 | Critical |
| **Policy** | YAML policy pack management and simulation | 3002 | Critical |
| **Evidence** | Audit trail storage, compliance reporting | 3003 | High |
| **Approvals** | Human-in-the-loop workflows | 3004 | Medium |
| **Fabric** | Agent policy fabric registry and control plane | 3005 | Medium |
| **Dashboard** | Web UI for monitoring and management | 3100 | Low |

---

## Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client  # v1.28+

# Kustomize
kustomize version  # v5.0+

# Helm (optional, for dependencies)
helm version  # v3.12+

# PostgreSQL client (for migrations)
psql --version  # v14+
```

### Required Access

- Kubernetes cluster with admin access
- Container registry access (ghcr.io or private)
- DNS management for service endpoints
- TLS certificate provisioning (cert-manager recommended)

---

## Infrastructure Requirements

### Minimum Production Requirements

| Component | CPU | Memory | Storage | Replicas |
|-----------|-----|--------|---------|----------|
| Enforcer | 2 cores | 2 GB | - | 3 |
| Evidence | 1 core | 1 GB | - | 2 |
| Approvals | 1 core | 1 GB | - | 2 |
| Dashboard | 0.5 core | 512 MB | - | 2 |
| PostgreSQL | 4 cores | 8 GB | 100 GB SSD | 2 (primary + replica) |
| Redis | 1 core | 2 GB | 10 GB SSD | 3 (sentinel) |

### Recommended Production Requirements

| Component | CPU | Memory | Storage | Replicas |
|-----------|-----|--------|---------|----------|
| Enforcer | 4 cores | 4 GB | - | 5-20 (autoscaled) |
| Evidence | 2 cores | 2 GB | - | 3-10 (autoscaled) |
| Approvals | 2 cores | 2 GB | - | 3-6 (autoscaled) |
| Dashboard | 1 core | 1 GB | - | 2-4 |
| PostgreSQL | 8 cores | 32 GB | 500 GB SSD | 3 (1 primary, 2 replicas) |
| Redis | 2 cores | 4 GB | 20 GB SSD | 6 (3 masters, 3 replicas) |

---

## Deployment Options

### Option 1: Kubernetes with Kustomize (Recommended)

```bash
# Clone the repository
git clone https://github.com/stix-ai/stix.git
cd stix

# Configure secrets (NEVER commit these)
cp infra/k8s/base/secrets.yaml.example infra/k8s/overlays/production/secrets.yaml
# Edit secrets.yaml with real values

# Deploy
kustomize build infra/k8s/overlays/production | kubectl apply -f -

# Verify deployment
kubectl get pods -n stix
kubectl get services -n stix
```

### Option 2: Helm Chart

```bash
# Add STIX Helm repository
helm repo add stix https://charts.stix.ai
helm repo update

# Install
helm install stix stix/stix \
  --namespace stix \
  --create-namespace \
  --values values-production.yaml

# Upgrade
helm upgrade stix stix/stix \
  --namespace stix \
  --values values-production.yaml
```

### Option 3: Docker Compose (Development/Testing Only)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Kubernetes Deployment

### Step 1: Create Namespace

```bash
kubectl create namespace stix
kubectl label namespace stix \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted
```

### Step 2: Configure Secrets

Use External Secrets Operator for production:

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: stix-secrets
  namespace: stix
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: stix-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: stix/production/database
        property: url
    - secretKey: JWT_PRIVATE_KEY
      remoteRef:
        key: stix/production/jwt
        property: private_key
```

### Step 3: Deploy Database

```bash
# Option A: Managed PostgreSQL (Recommended)
# Use AWS RDS, Google Cloud SQL, or Azure Database

# Option B: In-cluster PostgreSQL
helm install stix-postgres bitnami/postgresql \
  --namespace stix \
  --set auth.postgresPassword=$POSTGRES_PASSWORD \
  --set primary.persistence.size=100Gi \
  --set replication.enabled=true
```

### Step 4: Run Migrations

```bash
# Port-forward to database
kubectl port-forward svc/stix-postgres 5432:5432 -n stix &

# Run migrations
export DATABASE_URL="postgresql://stix:password@localhost:5432/stix"
./infra/migrations/migrate.sh up
```

### Step 5: Deploy Services

```bash
# Production deployment
kustomize build infra/k8s/overlays/production | kubectl apply -f -

# Verify
kubectl rollout status deployment/stix-enforcer -n stix
kubectl rollout status deployment/stix-evidence -n stix
kubectl rollout status deployment/stix-approvals -n stix
```

### Step 6: Configure Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: stix-ingress
  namespace: stix
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - stix.yourdomain.com
        - api.stix.yourdomain.com
      secretName: stix-tls
  rules:
    - host: stix.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: stix-dashboard
                port:
                  number: 3100
    - host: api.stix.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: stix-enforcer
                port:
                  number: 3001
```

---

## Security Configuration

### TLS/mTLS

```bash
# Generate Ed25519 keys for JWT signing
openssl genpkey -algorithm ed25519 -out jwt-private.pem
openssl pkey -in jwt-private.pem -pubout -out jwt-public.pem

# Create Kubernetes secret
kubectl create secret generic stix-jwt-keys \
  --from-file=private.pem=jwt-private.pem \
  --from-file=public.pem=jwt-public.pem \
  -n stix
```

### Network Policies

Network policies are included in the base deployment. They enforce:

- Default deny all ingress/egress
- Allow DNS resolution
- Allow traffic between STIX services only
- Allow ingress from ingress controller
- Allow Prometheus scraping from monitoring namespace

### Pod Security

All STIX containers run with:

- Non-root user (UID 1000)
- Read-only root filesystem
- Dropped all capabilities
- seccomp profile: RuntimeDefault
- No privilege escalation

---

## High Availability

### Database HA

```yaml
# PostgreSQL HA with Patroni
apiVersion: acid.zalan.do/v1
kind: postgresql
metadata:
  name: stix-postgres-cluster
spec:
  teamId: "stix"
  volume:
    size: 100Gi
  numberOfInstances: 3
  postgresql:
    version: "15"
  patroni:
    failsafe_mode: true
```

### Redis HA

```bash
helm install stix-redis bitnami/redis \
  --namespace stix \
  --set sentinel.enabled=true \
  --set replica.replicaCount=3 \
  --set sentinel.quorum=2
```

### Service HA

Pod Disruption Budgets ensure availability during updates:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: stix-enforcer-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/component: enforcer
```

---

## Monitoring & Observability

### Prometheus Metrics

```bash
# Deploy ServiceMonitor for Prometheus Operator
kubectl apply -f infra/k8s/overlays/production/servicemonitor.yaml

# Key metrics to monitor:
# - stix_authorization_total
# - stix_authorization_duration_seconds
# - stix_evidence_write_total
# - stix_approvals_pending
```

### Grafana Dashboards

Import the included Grafana dashboards:

```bash
kubectl create configmap stix-grafana-dashboards \
  --from-file=dashboards/ \
  -n monitoring
```

### Distributed Tracing

Configure OpenTelemetry:

```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://otel-collector.observability:4318"
  - name: TRACING_ENABLED
    value: "true"
  - name: TRACING_SAMPLE_RATE
    value: "0.01"  # 1% sampling in production
```

### Alerting

Critical alerts are defined in `servicemonitor.yaml`:

| Alert | Severity | Condition |
|-------|----------|-----------|
| StixEnforcerDown | Critical | Service unavailable > 1m |
| StixEnforcerHighLatency | Warning | p99 latency > 500ms for 5m |
| StixEnforcerHighDenyRate | Warning | > 50% denials for 10m |
| StixEvidenceChainBroken | Critical | Hash chain verification failure |
| StixApprovalsBacklog | Warning | > 100 pending approvals for 30m |

---

## Backup & Recovery

### Database Backup

```bash
# Continuous backup with pgBackRest
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: stix-backup
  namespace: stix
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: pgbackrest/pgbackrest:latest
            command: ["/bin/sh", "-c"]
            args:
              - pgbackrest --stanza=stix backup --type=incr
          restartPolicy: OnFailure
EOF
```

### Evidence Export

```bash
# Export evidence for compliance audit
pnpm stix-cli evidence export \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --format jsonl \
  --output evidence-2024.jsonl.gz
```

### Disaster Recovery

1. **RTO Target**: < 15 minutes
2. **RPO Target**: < 1 minute (with synchronous replication)

Recovery procedure:

```bash
# 1. Restore database from backup
pgbackrest --stanza=stix restore --target-time="2024-01-15 10:00:00"

# 2. Verify evidence chain integrity
pnpm stix-cli evidence verify-chain

# 3. Redeploy services
kustomize build infra/k8s/overlays/production | kubectl apply -f -

# 4. Reload policies
pnpm stix-cli policy deploy policies/ --api-url $STIX_API_URL
```

---

## Scaling Guidelines

### Horizontal Scaling

The Enforcer service scales based on:

- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Requests per second (target: 1000 RPS per pod)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stix-enforcer-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stix-enforcer
  minReplicas: 5
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Capacity Planning

| Authorization Volume | Enforcer Pods | Database Size |
|---------------------|---------------|---------------|
| 1M/day | 3 | 50 GB/year |
| 10M/day | 10 | 500 GB/year |
| 100M/day | 30 | 5 TB/year |
| 1B/day | 100+ | 50 TB/year |

---

## Compliance Considerations

### Data Retention

Configure retention policies in PostgreSQL:

```sql
-- Automatic evidence partition management
SELECT create_evidence_partition(date_trunc('month', NOW() + interval '1 month'));

-- Archive old partitions
ALTER TABLE evidence_y2023m01 SET TABLESPACE archive_storage;
```

### Audit Requirements

| Regulation | Evidence Retention | Encryption | Access Logging |
|------------|-------------------|------------|----------------|
| SOX | 7 years | Required | Required |
| HIPAA | 6 years | Required | Required |
| GDPR | Per policy | Required | Required |
| PCI-DSS | 1 year | Required | Required |

### Evidence Integrity

STIX maintains evidence integrity through:

1. **Hash Chain**: Each event includes hash of previous event
2. **Digital Signatures**: Ed25519 signatures on all events
3. **Immutability**: Append-only evidence store
4. **Verification**: Regular chain integrity checks

---

## Troubleshooting

### Common Issues

#### 1. Enforcer Not Starting

```bash
# Check logs
kubectl logs -l app.kubernetes.io/component=enforcer -n stix

# Common causes:
# - Database connection failed
# - Missing JWT keys
# - Policy validation errors
```

#### 2. High Authorization Latency

```bash
# Check policy cache hit rate
curl -s http://localhost:9090/metrics | grep policy_cache

# Possible solutions:
# - Increase cache TTL
# - Add more enforcer replicas
# - Optimize policy structure
```

#### 3. Evidence Write Failures

```bash
# Check evidence service logs
kubectl logs -l app.kubernetes.io/component=evidence -n stix

# Verify database connectivity
kubectl exec -it deploy/stix-evidence -n stix -- \
  wget -q -O- http://localhost:3003/health
```

#### 4. Approval Timeouts

```bash
# Check pending approvals
curl -s http://localhost:3004/api/v1/approvals?status=pending | jq '.data | length'

# Increase timeout or notification frequency
```

### Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic liveness check |
| `/health/ready` | Readiness check (includes dependencies) |
| `/health/live` | Kubernetes liveness probe |
| `/metrics` | Prometheus metrics |

### Support Channels

- GitHub Issues: https://github.com/stix-ai/stix/issues
- Security Issues: security@stix.ai
- Enterprise Support: enterprise@stix.ai

---

## Quick Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_PRIVATE_KEY` | Ed25519 private key (PEM) | Required |
| `JWT_PUBLIC_KEY` | Ed25519 public key (PEM) | Required |
| `LOG_LEVEL` | Logging level | `info` |
| `METRICS_ENABLED` | Enable Prometheus metrics | `true` |
| `TRACING_ENABLED` | Enable OpenTelemetry tracing | `true` |

### Useful Commands

```bash
# Deploy to staging
kustomize build infra/k8s/overlays/staging | kubectl apply -f -

# Deploy to production
kustomize build infra/k8s/overlays/production | kubectl apply -f -

# Run database migrations
./infra/migrations/migrate.sh up

# Validate policies
pnpm stix-cli policy validate policies/

# Deploy policies
pnpm stix-cli policy deploy policies/ --api-url $STIX_API_URL

# Export evidence
pnpm stix-cli evidence export --format jsonl --output evidence.jsonl

# Verify evidence chain
pnpm stix-cli evidence verify-chain --trace-id $TRACE_ID
```
