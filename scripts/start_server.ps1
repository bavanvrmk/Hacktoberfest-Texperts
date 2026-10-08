# scripts/start_server.ps1
# Configures llama-server.exe on port 8080 with GPU offloading (-ngl 99)

$LlamaServer = "llama-server.exe" # Assumes it's in PATH
$ModelFile = "models/qwen2.5-vl-3b-instruct-q4_k_m.gguf"
$ProjFile = "models/mmproj-model-f16.gguf"
$Port = 8080

Write-Host "Starting llama-server on port $Port with GPU offloading..."
Write-Host "Run this command when models are downloaded:"
Write-Host "& $LlamaServer -m $ModelFile --mmproj $ProjFile -ngl 99 --port $Port -c 4096"
