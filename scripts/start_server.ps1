# scripts/start_server.ps1
# Starts llama-server on port 8080 with GPU offloading (-ngl 99).

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$ModelName = "kv-ground-4b-q4_k_m.gguf"
$ProjName = "mmproj-Qwen3VL-4B-Instruct-F16.gguf"
$Port = 8080
$GpuLayers = 99
$Context = 4096

function Find-RepoFile([string]$Name) {
    foreach ($dir in @("Models", "models")) {
        $candidate = Join-Path (Join-Path $Root $dir) $Name
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

$ModelFile = Find-RepoFile $ModelName
$ProjFile = Find-RepoFile $ProjName

$LlamaCmd = Get-Command "llama-server.exe" -ErrorAction SilentlyContinue
if (-not $LlamaCmd) {
    $localBin = Join-Path $Root "llama-server.exe"
    if (Test-Path -LiteralPath $localBin) {
        $LlamaServer = $localBin
    }
} else {
    $LlamaServer = $LlamaCmd.Source
}

$missing = @()
if (-not $ModelFile) { $missing += $ModelName }
if (-not $ProjFile) { $missing += $ProjName }
if (-not $LlamaServer) { $missing += "llama-server.exe" }

if ($missing.Count -gt 0) {
    Write-Host "Cannot start llama-server. Missing:"
    $missing | ForEach-Object { Write-Host "  $_" }
    Write-Host "Looked in $Root\Models and $Root\models, and on PATH for llama-server.exe."
    exit 1
}

Write-Host "Starting llama-server on port $Port with GPU offloading..."
Write-Host "  binary: $LlamaServer"
Write-Host "  model:  $ModelFile"
Write-Host "  mmproj: $ProjFile"

& $LlamaServer -m $ModelFile --mmproj $ProjFile -ngl $GpuLayers --port $Port -c $Context --image-min-tokens 1024
exit $LASTEXITCODE
