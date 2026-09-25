param([string]$Projeto = "")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$projetos = @(
    [pscustomobject]@{ Nome = "Aula_01_Revisao_LangChain_LCEL_ChatOllama"; Tipo = "React + FastAPI"; Porta = "8101" }
    [pscustomobject]@{ Nome = "Aula_02_Memoria_Conversacional"; Tipo = "React + FastAPI"; Porta = "8102" }
    [pscustomobject]@{ Nome = "Aula_03_Structured_Output_Pydantic_v2"; Tipo = "React + FastAPI"; Porta = "8103" }
    [pscustomobject]@{ Nome = "Aula_04_Context_Engineering"; Tipo = "React + FastAPI"; Porta = "8104" }
    [pscustomobject]@{ Nome = "Aula_05_Embeddings_Busca_Semantica_ChromaDB"; Tipo = "React + FastAPI"; Porta = "8105" }
    [pscustomobject]@{ Nome = "Aula_06_Pipeline_RAG_Completo"; Tipo = "React + FastAPI"; Porta = "8106" }
    [pscustomobject]@{ Nome = "Aula_07_RAG_Avancado_Chunking_RAGAS"; Tipo = "React + FastAPI"; Porta = "8107" }
    [pscustomobject]@{ Nome = "Aula_08_Interfaces_Gradio_Streamlit_Deploy"; Tipo = "Gradio + Streamlit"; Porta = "7860" }
    [pscustomobject]@{ Nome = "Aula_09_Agentes_ReAct_Tools_FunctionCalling"; Tipo = "React + FastAPI"; Porta = "8109" }
    [pscustomobject]@{ Nome = "Aula_10_ContextEngineering_Agentes_MCP"; Tipo = "React + FastAPI"; Porta = "8110" }
    [pscustomobject]@{ Nome = "Aula_11_Integradora_Agente_RAG_Gradio"; Tipo = "Gradio"; Porta = "7860" }
    [pscustomobject]@{ Nome = "Aula_12_RouterChain_GrafoEstado"; Tipo = "React + FastAPI"; Porta = "8112" }
    [pscustomobject]@{ Nome = "Aula_13_LangGraph_StateGraph_HITL"; Tipo = "React + FastAPI"; Porta = "8113" }
    [pscustomobject]@{ Nome = "Aula_14_SpecDrivenDevelopment_Encerramento"; Tipo = "React + FastAPI"; Porta = "8114" }
    [pscustomobject]@{ Nome = "Bonus_MultiChains_MultiModelos"; Tipo = "React + FastAPI"; Porta = "8199" }
)

Write-Host "Selecione o projeto que deseja configurar:" -ForegroundColor Cyan
for ($indice = 0; $indice -lt $projetos.Count; $indice++) {
    $item = $projetos[$indice]
    $numero = $indice + 1
    Write-Host ("{0,2}. {1} [{2}] - porta {3}" -f $numero, $item.Nome, $item.Tipo, $item.Porta)
}

if ([string]::IsNullOrWhiteSpace($Projeto)) {
    $Projeto = Read-Host "Digite o numero ou parte do nome do projeto"
}

if ($Projeto -match "^[0-9]+$") {
    $numero = [int]$Projeto
    if ($numero -lt 1 -or $numero -gt $projetos.Count) {
        throw "Numero de projeto invalido: $Projeto"
    }
    $selecionado = $projetos[$numero - 1]
} else {
    $candidatos = @($projetos | Where-Object {
        $_.Nome.IndexOf($Projeto, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    if ($candidatos.Count -eq 0) {
        throw "Nenhum projeto corresponde a: $Projeto"
    }
    if ($candidatos.Count -gt 1) {
        throw "Escreva um trecho mais especifico para o projeto: $Projeto"
    }
    $selecionado = $candidatos[0]
}

$caminhoProjeto = Join-Path $PSScriptRoot $selecionado.Nome
$caminhoSetup = Join-Path $caminhoProjeto "setup.ps1"
if (-not (Test-Path -LiteralPath $caminhoSetup -PathType Leaf)) {
    throw "setup.ps1 nao encontrado em $($selecionado.Nome)."
}

Write-Host "Configurando $($selecionado.Nome)..." -ForegroundColor Cyan
& $caminhoSetup
if (-not $?) {
    throw "A configuracao de $($selecionado.Nome) terminou com falha."
}

Write-Host "Configuracao concluida: $($selecionado.Nome)" -ForegroundColor Green
