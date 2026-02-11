param(
  [ValidateSet("build","open","status","listen","help")]
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
function Raven-Say {
  param([string]$Text)
  try {
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.Speak($Text)
  } catch {
    # If speech isn't available, fail silently
  }
}

switch ($Action) {
		"listen" {
	  Raven-Say "Raven is listening. Say update codex, open codex, status, or stop listening."

	  Add-Type -AssemblyName System.Speech
	  $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine
	  $choices = New-Object System.Speech.Recognition.Choices
	  $choices.Add(@("update codex","open codex","status","stop listening"))

	  $gb = New-Object System.Speech.Recognition.GrammarBuilder
	  $gb.Append($choices)
	  $grammar = New-Object System.Speech.Recognition.Grammar($gb)

	  $rec.LoadGrammar($grammar)
	  $rec.SetInputToDefaultAudioDevice()
	  $rec.RecognizeTimeout = New-TimeSpan -Seconds 10

	  while ($true) {
		Write-Host "🎙️ Listening..." -ForegroundColor Cyan
		$result = $rec.Recognize()
		if (-not $result) { continue }

		$spoken = $result.Text.ToLowerInvariant()
		Write-Host "🗣️ Heard: $spoken" -ForegroundColor DarkCyan

		switch ($spoken) {
		  "update codex" {
			Raven-Say "Updating codex."
			python (Join-Path $root "tools\codex\build_codex.py") $root
			Raven-Say "Codex updated."
		  }
		  "open codex" {
			Raven-Say "Opening codex."
			Start-Process (Join-Path $root "README.md")
		  }
		  "status" {
			Raven-Say "Checking status."
			Push-Location $root
			git status
			Pop-Location
		  }
		  "stop listening" {
			Raven-Say "Stopping."
			break
		  }
		}
	  }
	}
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
