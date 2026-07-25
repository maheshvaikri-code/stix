$env:NODE_ENV = "test"
$env:PORT = "4011"
$env:LOG_LEVEL = "error"
$env:LOG_PRETTY = "false"
$env:POLICY_SERVICE_URL = "http://localhost:4012"
$env:EVIDENCE_SERVICE_URL = "http://localhost:4013"
$env:APPROVALS_SERVICE_URL = "http://localhost:4014"
$env:USE_MOCK_CLIENTS = "false"
$env:REDIS_ENABLED = "false"
$env:CACHE_ENABLED = "false"
$env:EVIDENCE_WRITE_MODE = "strict"

pnpm --filter @stix/enforcer start
