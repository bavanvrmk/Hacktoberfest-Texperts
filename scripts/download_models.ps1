# scripts/download_models.ps1
# Script to download Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf & mmproj

$ModelDir = "models"
if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Path $ModelDir | Out-Null
}

# Note: These URLs point to the ShuaiBai623 repository
$ModelUrl = "https://huggingface.co/ShuaiBai623/Qwen3VL-4B-Instruct-GGUF/resolve/main/Qwen3VL-4B-Instruct-Q4_K_M.gguf?download=true"
$ProjUrl = "https://huggingface.co/ShuaiBai623/Qwen3VL-4B-Instruct-GGUF/resolve/main/mmproj-Qwen3VL-4B-Instruct-F16.gguf?download=true"

$ModelFile = Join-Path $ModelDir "Qwen3VL-4B-Instruct-Q4_K_M.gguf"
$ProjFile = Join-Path $ModelDir "mmproj-Qwen3VL-4B-Instruct-F16.gguf"

Write-Host "Downloading model file..."
# Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile

Write-Host "Downloading mmproj file..."
# Invoke-WebRequest -Uri $ProjUrl -OutFile $ProjFile

Write-Host "Download script ready."
