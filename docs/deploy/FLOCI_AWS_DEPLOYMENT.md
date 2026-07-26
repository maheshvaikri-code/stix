# STIX Floci AWS Deployment

This deployment path runs STIX Core, STIX Fabric, the dashboard, Postgres, Redis, and Floci in one isolated Docker Compose project.

Floci provides a local AWS-compatible endpoint for FDE and Doctrine deployment drills without requiring real AWS credentials.

## Stack

| Component | Container | Host port |
|---|---|---|
| Floci AWS emulator | `stix-floci` | `4566` |
| Enforcer | `stix-enforcer` | `3001` |
| Policy | `stix-policy` | `3002` |
| Evidence | `stix-evidence` | `3003` |
| Approvals | `stix-approvals` | `3004` |
| Fabric | `stix-fabric` | `3005` |
| Dashboard | `stix-dashboard` | `3100` |
| Postgres | `stix-postgres` | `5432` |
| Redis | `stix-redis` | `6379` |

## Deploy

```bash
docker compose -f deploy/docker/docker-compose.yaml up -d --build
```

The Compose file sets `name: stix`, which creates an isolated project and network. Avoid `--remove-orphans` unless you are certain only STIX containers are attached to the project.

## Verify

The recommended full gate is:

```bash
pnpm deploy:fde:floci
```

This command validates Compose config, builds and starts the stack, waits for health, seeds Doctrine/Fabric records, checks readiness, smokes dashboard routes, verifies Floci S3-compatible artifact round trip, and writes `artifacts/deploy/floci-fde-gate-report.json`.

Use teardown mode in CI:

```bash
pnpm deploy:fde:floci -- --teardown
```

The same gate runs in GitHub Actions through `.github/workflows/floci-fde.yml` when deployment, Fabric, dashboard, or FDE scripts change.

```bash
curl http://localhost:3001/health
curl http://localhost:3002/health
curl http://localhost:3003/health
curl http://localhost:3004/health
curl http://localhost:3005/health
curl http://localhost:4566/
```

Seed the Doctrine/Fabric registry and verify readiness:

```bash
pnpm demo:fabric:seed
curl http://localhost:3005/api/v1/fabric/readiness
```

Run the Floci AWS smoke:

```bash
pnpm deploy:floci:smoke
```

Open the deployed dashboard:

```text
http://localhost:3100/fabric
http://localhost:3100/doctrine
```

## Notes

- Floci is local AWS emulation, not a real AWS account deployment.
- STIX services receive `AWS_ENDPOINT_URL=http://floci:4566` plus deterministic local test credentials.
- Durable STIX state remains in Postgres for this stack.
- Floci is currently used for AWS-shaped FDE artifact smoke validation.
- For real AWS deployment, use the Kubernetes/EKS or ECS path with managed Postgres, Redis, KMS or secret-managed signing keys, and real AWS IAM boundaries.

## Cleanup

```bash
docker compose -f deploy/docker/docker-compose.yaml down
```

Do not add `--volumes` unless you intentionally want to delete local Postgres, Redis, and Floci state.
