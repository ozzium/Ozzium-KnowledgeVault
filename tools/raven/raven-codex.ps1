param(
  [ValidateSet("build","open","status","help")]
  [string]$Action = "help",
  [string]$VaultPath = ""
)

function Resolve-VaultPath {
  param([string]$P)
  if ($P -and (Test-Path $P)) { return (Resolve-Path $P).Path }

  # Default: assumes you're running inside the vault or a subfolder
  $here = (Get-Location).Path
  $probe = $here
  while ($probe -and (Test-Path $probe)) {
    if (Test-Path (Join-Path $probe "codex.config.json")) { return $probe }
    $parent = Split-Path $probe -Parent
    if ($parent -eq $probe) { break }
    $probe = $parent
  }
  throw "Vault root not found. Provide -VaultPath pointing to Ozzium-KnowledgeVault."
}

$root = Resolve-VaultPath $VaultPath

switch ($Action) {
  "build" {
    Write-Host "🧠 Raven: generating Codex..." -ForegroundColor Cyan
    python (Join-Path $root "tools\codex\build_codex.py") $root
    Write-Host "✅ Raven: Codex updated." -ForegroundColor Green
  }
  "open" {
    $readme = Join-Path $root "README.md"
    Write-Host "📖 Raven: opening $readme" -ForegroundColor Cyan
    Start-Process $readme
  }
  "status" {
    Write-Host "📦 Raven: git status for vault" -ForegroundColor Cyan
    Push-Location $root
    git status
    Pop-Location
  }
  default {
    Write-Host @"
raven-codex build   # regenerate README Codex locally
raven-codex open    # open README
raven-codex status  # git status
raven-codex help
"@
  }
}
