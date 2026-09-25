param([int]$Porta = 8102)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Find-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Nomes
    )

    foreach ($nome in $Nomes) {
        $comando = Get-Command $nome -CommandType Application -ErrorAction SilentlyContinue
        if ($null -ne $comando) {
            return $comando.Source
        }
    }

    throw "Executavel nao encontrado: $($Nomes -join ', ')"
}

$python = Find-NativeCommand -Nomes @("python", "python.exe", "py", "py.exe")
$node = Find-NativeCommand -Nomes @("node", "node.exe")
$npm = Find-NativeCommand -Nomes @("npm.cmd", "npm.exe", "npm")

& $python --version
if ($LASTEXITCODE -ne 0) { throw "Falha ao validar o Python." }
& $node --version
if ($LASTEXITCODE -ne 0) { throw "Falha ao validar o Node.js." }
& $npm --version
if ($LASTEXITCODE -ne 0) { throw "Falha ao validar o npm." }

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $PSScriptRoot "requirements.txt"
$frontend = Join-Path $PSScriptRoot "frontend"
$packageJson = Join-Path $frontend "package.json"
$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) { throw "requirements.txt nao encontrado." }
if (-not (Test-Path -LiteralPath $packageJson -PathType Leaf)) { throw "frontend/package.json nao encontrado." }

if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
    if (-not (Test-Path -LiteralPath $envExample -PathType Leaf)) { throw ".env.example nao encontrado." }
    Copy-Item -LiteralPath $envExample -Destination $envFile -ErrorAction Stop
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & $python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o .venv." }
}
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw ".venv criado sem python.exe." }

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar o pip." }
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias Python." }

Push-Location -LiteralPath $frontend
try {
    $lockFile = Join-Path $frontend "package-lock.json"
    if (Test-Path -LiteralPath $lockFile -PathType Leaf) {
        & $npm ci --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) { throw "Falha no npm ci." }
    } else {
        & $npm install --no-fund --no-audit
        if ($LASTEXITCODE -ne 0) { throw "Falha no npm install." }
    }

    & $npm run build
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do frontend." }
} finally {
    Pop-Location
}

Write-Host "[ok] servidor em http://127.0.0.1:$Porta"
& $venvPython -m uvicorn server:app --host 127.0.0.1 --port $Porta
if ($LASTEXITCODE -ne 0) { throw "Uvicorn terminou com codigo $LASTEXITCODE." }
