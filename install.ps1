$ErrorActionPreference = "Stop"

# 1. Definição de caminhos para a instalação
$installDir = Join-Path $HOME ".ducknano"
$tempZip = Join-Path $env:TEMP "ducknano.zip"
$tempExtract = Join-Path $env:TEMP "ducknano_extracted"

Write-Host "🦆 Iniciando a instalação do DuckNano..." -ForegroundColor Cyan

# 2. Verificação de pré-requisitos (Python)
Write-Host "🔍 Verificando se o Python está instalado..." -ForegroundColor Gray
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Error "Python não foi encontrado no sistema. Por favor, instale o Python 3.10+ e adicione-o ao PATH antes de continuar."
    exit 1
}

# 3. Limpeza de instalações anteriores
if (Test-Path $installDir) {
    Write-Host "🧹 Instalação anterior detectada. Removendo arquivos antigos..." -ForegroundColor Gray
    try {
        Remove-Item $installDir -Recurse -Force
    } catch {
        Write-Warning "Não foi possível remover completamente a pasta antiga. Prosseguindo com a sobreposição..."
    }
}
New-Item -ItemType Directory -Path $installDir -Force | Out-Null

# 4. Download do código-fonte do GitHub
Write-Host "📥 Baixando DuckNano do GitHub..." -ForegroundColor Gray
$zipUrl = "https://github.com/wanbnn/ducknano/archive/refs/heads/main.zip"
try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -UseBasicParsing
} catch {
    Write-Error "Falha ao baixar o repositório do GitHub. Verifique sua conexão com a internet."
    exit 1
}

# 5. Extração do conteúdo baixado
Write-Host "📦 Extraindo arquivos..." -ForegroundColor Gray
if (Test-Path $tempExtract) {
    Remove-Item $tempExtract -Recurse -Force | Out-Null
}
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

# Localiza a pasta extraída (geralmente 'ducknano-main') e copia os arquivos para o diretório final
$extractedFolder = Get-ChildItem -Path $tempExtract -Directory | Select-Object -First 1
Copy-Item -Path "$($extractedFolder.FullName)\*" -Destination $installDir -Recurse -Force

# Limpeza de arquivos temporários de download
Remove-Item $tempZip -Force
Remove-Item $tempExtract -Recurse -Force

# 6. Criação do Ambiente Virtual (venv)
Write-Host "🐍 Criando o ambiente virtual Python (venv)..." -ForegroundColor Gray
& python -m venv "$installDir\venv"

# 7. Instalação das dependências
Write-Host "⚙️ Instalando as dependências do projeto..." -ForegroundColor Gray
$pipPath = Join-Path $installDir "venv\Scripts\pip.exe"
$reqFile = Join-Path $installDir "requirements.txt"

if (Test-Path $reqFile) {
    # Tenta instalar direto do requirements.txt se ele existir
    & $pipPath install -r $reqFile
} else {
    # Fallback manual para as bibliotecas especificadas
    & $pipPath install requests rich
}

# 8. Criação dos executáveis wrappers na pasta de instalação
# Esses scripts servem de ponte para rodar o app.py usando o python da venv, independente de onde o usuário os chame
Write-Host "🔨 Gerando os arquivos de inicialização..." -ForegroundColor Gray

# Wrapper para CMD / Git Bash / PowerShell comum (ducknano.cmd)
$cmdContent = @"
@echo off
"%~dp0venv\Scripts\python.exe" "%~dp0app.py" %*
"@
$cmdContent | Out-File -FilePath (Join-Path $installDir "ducknano.cmd") -Encoding ascii -Force

# Wrapper nativo para PowerShell (ducknano.ps1)
$ps1Content = @"
`$scriptDir = Split-Path `$MyInvocation.MyCommand.Path
& "`$scriptDir\venv\Scripts\python.exe" "`$scriptDir\app.py" `$args
"@
$ps1Content | Out-File -FilePath (Join-Path $installDir "ducknano.ps1") -Encoding utf8 -Force

# 9. Configuração do PATH do usuário
Write-Host "🔗 Adicionando DuckNano ao PATH do usuário..." -ForegroundColor Gray
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathElements = $userPath -split ";" | Where-Object { $_ -ne "" }

if ($pathElements -contains $installDir) {
    Write-Host "✅ O diretório do DuckNano já consta no seu PATH." -ForegroundColor Green
} else {
    $pathElements += $installDir
    $newUserPath = $pathElements -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    
    # Atualiza a sessão atual do console também
    $env:Path = "$env:Path;$installDir"
    Write-Host "✅ Caminho adicionado com sucesso ao PATH." -ForegroundColor Green
}

Write-Host "`n🎉 Instalação do DuckNano concluída!" -ForegroundColor Green
Write-Host "Para utilizar, abra uma NOVA janela do terminal e digite: ducknano" -ForegroundColor Cyan