param(
    [string]$Python = "python"
)

$pastaProjeto = Split-Path -Parent $MyInvocation.MyCommand.Path
$pastaAmbiente = Join-Path $pastaProjeto ".venv"
$executavelPython = Join-Path $pastaAmbiente "Scripts\python.exe"
$pastaDistribuicao = Join-Path $pastaProjeto "dist"
$caminhoExecutavel = Join-Path $pastaDistribuicao "EditorRAW.exe"

$processoAberto = Get-Process -Name "EditorRAW" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $caminhoExecutavel }
if ($processoAberto) {
    throw "Feche o EditorRAW.exe antes de gerar uma nova versão."
}

if (-not (Test-Path -LiteralPath $executavelPython)) {
    & $Python -m venv $pastaAmbiente
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível criar o ambiente virtual."
    }
}

& $executavelPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível atualizar o pip."
}
& $executavelPython -m pip install -r (Join-Path $pastaProjeto "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível instalar as dependências."
}

$versaoPython = & $executavelPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($versaoPython -ne "3.12") {
    throw "A geração padronizada requer Python 3.12; encontrado: $versaoPython."
}

& $executavelPython -m py_compile `
    (Join-Path $pastaProjeto "app.py") `
    (Join-Path $pastaProjeto "editor_mascara.py") `
    (Join-Path $pastaProjeto "efeitos.py") `
    (Join-Path $pastaProjeto "modelos.py") `
    (Join-Path $pastaProjeto "presets.py") `
    (Join-Path $pastaProjeto "processamento.py") `
    (Join-Path $pastaProjeto "versao.py")
if ($LASTEXITCODE -ne 0) {
    throw "A validação de sintaxe falhou."
}

& $executavelPython -m unittest discover `
    -s (Join-Path $pastaProjeto "tests") `
    -v
if ($LASTEXITCODE -ne 0) {
    throw "Os testes falharam; o executável não será gerado."
}

& $executavelPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "EditorRAW" `
    --collect-all rawpy `
    --distpath $pastaDistribuicao `
    --workpath (Join-Path $pastaProjeto "build") `
    --specpath $pastaProjeto `
    (Join-Path $pastaProjeto "app.py")
if ($LASTEXITCODE -ne 0) {
    throw "A geração do executável falhou. Feche o EditorRAW.exe e tente novamente."
}

$versaoAplicativo = & $executavelPython -c "from versao import VERSAO_APLICATIVO; print(VERSAO_APLICATIVO)"
$hash = (Get-FileHash -LiteralPath $caminhoExecutavel -Algorithm SHA256).Hash
$dataBuild = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$informacoes = @(
    "EditorRAW $versaoAplicativo",
    "Build: $dataBuild",
    "Python: $versaoPython",
    "SHA256: $hash"
)
$informacoes | Set-Content -LiteralPath (Join-Path $pastaDistribuicao "build-info.txt") -Encoding utf8
Copy-Item -LiteralPath (Join-Path $pastaProjeto "README.md") -Destination $pastaDistribuicao -Force

Write-Host "Executável criado em: $caminhoExecutavel"
Write-Host "SHA256: $hash"
