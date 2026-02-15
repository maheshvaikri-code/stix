# STIX Transport Security Runbook

Date: 2026-02-14

## Scope

- Enforce mTLS on all in-cluster STIX service-to-service traffic.
- Maintain certificate rotation without service outage.
- Prohibit plaintext internal transport in production.

## Kubernetes Baseline

1. Deploy STIX base:
   - `kubectl apply -f deploy/k8s/stix-platform.yaml`
2. Deploy mTLS profile (Istio required):
   - `kubectl apply -f deploy/k8s/stix-mtls.yaml`
3. Verify strict mTLS:
   - `kubectl -n stix get peerauthentication stix-strict-mtls -o yaml`
   - Confirm `mode: STRICT`.

## Certificate Lifecycle

1. CA / issuer setup:
   - Use enterprise PKI-backed Istio CA or cert-manager issuer.
2. Rotation cadence:
   - Workload cert TTL <= 24h (automatic mesh rotation).
   - Root/intermediate CA rotation per enterprise PKI policy.
3. Rotation validation:
   - Confirm workload cert update on pods:
     - `kubectl -n stix exec <pod> -- ls /etc/certs`
   - Check no TLS handshake errors in sidecar logs.

## Production Gates

- `PeerAuthentication` in `STRICT` mode is active.
- Destination rules enforce `ISTIO_MUTUAL` for all STIX services.
- No service endpoints are reachable over plaintext from unauthorized namespaces.
- Certificate rotation drill completes without authorization/evidence outage.

