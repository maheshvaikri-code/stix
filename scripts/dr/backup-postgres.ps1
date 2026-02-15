param(
  [string]$ContainerName = "stix-postgres",
  [string]$DbName = "stix",
  [string]$DbUser = "stix",
  [string]$OutputDir = "artifacts\dr",
  [string]$Label = "manual"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputDir)) {
  New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$fileName = "stix_backup_${Label}_${timestamp}.sql"
$outputPath = Join-Path $OutputDir $fileName

Write-Host "Creating Postgres backup from container '$ContainerName'..."
docker exec $ContainerName pg_dump -U $DbUser $DbName | Out-File -FilePath $outputPath -Encoding utf8

if (-not (Test-Path $outputPath)) {
  throw "Backup file was not created: $outputPath"
}

$hash = Get-FileHash -Path $outputPath -Algorithm SHA256
Write-Host "Backup complete: $outputPath"
Write-Host "SHA256: $($hash.Hash)"
