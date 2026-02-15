param(
  [Parameter(Mandatory = $true)]
  [string]$BackupFile,
  [string]$ContainerName = "stix-postgres",
  [string]$DbName = "stix",
  [string]$DbUser = "stix"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
  throw "Backup file not found: $BackupFile"
}

Write-Host "Restoring backup '$BackupFile' into container '$ContainerName'..."
Get-Content -Path $BackupFile -Raw | docker exec -i $ContainerName psql -U $DbUser -d $DbName

Write-Host "Restore complete."
