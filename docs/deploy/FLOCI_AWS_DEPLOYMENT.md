# STIX Floci AWS Deployment

This deployment path runs STIX Core, STIX Fabric, the dashboard, Postgres, Redis, and Floci in one isolated Docker Compose project.

Doctrine/FDE is the governed operating module for executing this deployment drill. It is not a STIX Fabric product component. Floci provides the local AWS-compatible endpoint used by the drill without requiring real AWS credentials.

## Stack

| Component          | Compose service | Host port |
| ------------------ | --------------- | --------- |
| Floci AWS emulator | `floci`         | `4566`    |
| Enforcer           | `enforcer`      | `3001`    |
| Policy             | `policy`        | `3002`    |
| Evidence           | `evidence`      | `3003`    |
| Approvals          | `approvals`     | `3004`    |
| Fabric             | `fabric`        | `3005`    |
| Dashboard          | `dashboard`     | `3100`    |
| Postgres           | `postgres`      | `5432`    |
| Redis              | `redis`         | `6379`    |

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

This command validates the Doctrine/FDE local-only contract, builds and starts the stack, waits for health, seeds STIX Fabric product demo records, checks Fabric readiness, smokes dashboard routes, verifies a deterministic Floci S3-compatible artifact round trip, and writes `artifacts/deploy/floci-fde-gate-report.json`.

For fast preflight without starting containers:

```bash
pnpm deploy:fde:floci -- --check-only
```

Use teardown mode in CI:

```bash
pnpm deploy:fde:floci -- --teardown --reset-volumes
```

Use a separate Compose project name for isolated drills:

```bash
pnpm deploy:fde:floci -- --project-name=stix_fde_drill --teardown --reset-volumes
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

Seed the STIX Fabric demo registry and verify readiness:

```bash
pnpm demo:fabric:seed
curl http://localhost:3005/api/v1/fabric/readiness
```

Doctrine observer records are optional and are disabled by default:

```bash
STIX_DEMO_INCLUDE_DOCTRINE=true pnpm demo:fabric:seed
pnpm deploy:fde:floci -- --include-doctrine-observer
```

Run the Floci AWS smoke:

```bash
pnpm deploy:floci:smoke
```

Open the deployed dashboard:

```text
http://localhost:3100/fabric
```

## Notes

- Floci is local AWS emulation, not a real AWS account deployment.
- STIX services receive `AWS_ENDPOINT_URL=http://floci:4566` plus deterministic local test credentials.
- The Compose stack pins Floci with `FLOCI_IMAGE` defaulting to `floci/floci:1.5.11`; override only for an intentional emulator upgrade drill.
- Host `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are not passed into the stack; the local emulator always uses dummy `test` credentials.
- Durable STIX state remains in Postgres for this stack.
- Floci is currently used for AWS-shaped FDE artifact smoke validation and local deployment parity checks.
- Emulator-verified is not cloud-verified. Promotion to real AWS requires a separate human-reviewed plan and real-cloud smoke.
- For real AWS deployment, use the Kubernetes/EKS or ECS path with managed Postgres, Redis, KMS or secret-managed signing keys, and real AWS IAM boundaries.

## Cleanup

```bash
docker compose -f deploy/docker/docker-compose.yaml down
```

Do not add `--volumes` unless you intentionally want to delete local Postgres, Redis, and Floci state.
