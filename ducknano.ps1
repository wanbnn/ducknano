$ErrorActionPreference = "Stop"

Write-Host "DuckNano" -ForegroundColor Cyan

# Diretório do script
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Caminho da venv
$VenvDir = Join-Path $AppDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

# Adiciona ao PATH do usuário se ainda não existir
$UserPath = [Environment]::GetEnvironmentVariable(
    "Path",
    [EnvironmentVariableTarget]::User
)

if (-not ($UserPath -split ';' | Where-Object { $_ -eq $AppDir })) {
    $NewPath = if ([string]::IsNullOrWhiteSpace($UserPath)) {
        $AppDir
    }
    else {
        "$UserPath;$AppDir"
    }

    [Environment]::SetEnvironmentVariable(
        "Path",
        $NewPath,
        [EnvironmentVariableTarget]::User
    )

    Write-Host "Diretório adicionado ao PATH do usuário." -ForegroundColor Green
}

# Cria venv se não existir
if (-not (Test-Path $PythonExe)) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Yellow

    python -m venv $VenvDir

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar a venv. Verifique se o Python está instalado."
    }
}

# Atualiza pip
& $PythonExe -m pip install --upgrade pip

# Instala dependências
& $PythonExe -m pip install requests rich

# Executa aplicação
& $PythonExe (Join-Path $AppDir "app.py") @args