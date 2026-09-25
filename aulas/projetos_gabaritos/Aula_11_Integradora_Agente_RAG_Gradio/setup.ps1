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
& $python --version
if ($LASTEXITCODE -ne 0) { throw "Falha ao validar o Python." }

$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$requirements = Join-Path $PSScriptRoot "requirements.txt"
$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) { throw "requirements.txt nao encontrado." }

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

Write-Host "Ambiente pronto em $PSScriptRoot" -ForegroundColor Green
Write-Host "Execute python main.py para iniciar a interface Gradio." -ForegroundColor Green
