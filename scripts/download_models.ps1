# scripts/download_models.ps1
# Script to download Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf & mmproj

$ModelDir = "models"
if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Path $ModelDir | Out-Null
}

# Note: These URLs are placeholders for the actual GGUF downloads
$ModelUrl = "https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/qwen2.5-vl-3b-instruct-q4_k_m.gguf"
$ProjUrl = "https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/mmproj-model-f16.gguf"

$ModelFile = Join-Path $ModelDir "qwen2.5-vl-3b-instruct-q4_k_m.gguf"
$ProjFile = Join-Path $ModelDir "mmproj-model-f16.gguf"

Write-Host "Downloading model file..."
# Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile

Write-Host "Downloading mmproj file..."
# Invoke-WebRequest -Uri $ProjUrl -OutFile $ProjFile

Write-Host "Download script ready."
