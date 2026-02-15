param(
  [string]$EnforcerUrl = "http://localhost:3001",
  [string]$PolicyUrl = "http://localhost:3002",
  [string]$EvidenceUrl = "http://localhost:3003",
  [string]$ApprovalsUrl = "http://localhost:3004"
)

$ErrorActionPreference = "Stop"

function Test-Endpoint {
  param([string]$Url)
  try {
    $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -ne 200) {
      throw "Unexpected status code $($response.StatusCode) for $Url"
    }
    Write-Host "OK  $Url"
  } catch {
    throw "FAIL $Url : $($_.Exception.Message)"
  }
}

Write-Host "Running DR service verification..."
Test-Endpoint "$EnforcerUrl/health"
Test-Endpoint "$PolicyUrl/health"
Test-Endpoint "$EvidenceUrl/health"
Test-Endpoint "$ApprovalsUrl/health"

Write-Host "DR verification passed."
