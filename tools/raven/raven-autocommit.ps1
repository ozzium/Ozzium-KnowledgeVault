param(
  [string]$VaultPath = "",
  [int]$IntervalSeconds = 120,
  [string]$Branch = "main"
)

function Resolve-VaultPath {
  param([string]$P)
  if ($P -and (Test-Path $P)) { return (Resolve-Path $P).Path }
  $here = (Get-Location).Path
  if (Test-Path (Join-Path $here "codex.config.json")) { return $here }
  throw "Provide -VaultPath pointing to Ozzium-KnowledgeVault."
}

$root = Resolve-VaultPath $VaultPath

Write-Host "🦅 Raven AutoCommit is watching: $root" -ForegroundColor Cyan
Write-Host "⏱️ Interval: $IntervalSeconds seconds | Branch: $Branch" -ForegroundColor DarkCyan

while ($true) {
  try {
    Push-Location $root

    # update codex locally too (optional but nice)
    python (Join-Path $root "tools\codex\build_codex.py") $root | Out-Null

    $status = git status --porcelain
    if ($status) {
      git add -A
      $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
      git commit -m "auto: vault update ($ts)" | Out-Null
      git push origin $Branch | Out-Null
      Write-Host "✅ Pushed changes @ $ts" -ForegroundColor Green
    } else {
      Write-Host "… no changes" -ForegroundColor DarkGray
    }
  } catch {
    Write-Host "❌ AutoCommit error: $($_.Exception.Message)" -ForegroundColor Red
  } finally {
    Pop-Location
  }
  Start-Sleep -Seconds $IntervalSeconds
}
