# Inicia files2md con un solo comando: prepara lo que falte, levanta el servidor y abre el navegador.
#
#   Doble clic en iniciar.bat              -> uso normal
#   iniciar.bat -AccesoDirecto             -> además crea un acceso directo en el Escritorio
#   iniciar.bat -Puerto 9000               -> usar otro puerto
#
# Solo hace trabajo cuando hace falta:
#   - crea el entorno de Python la primera vez y reinstala dependencias si cambió pyproject.toml
#   - instala paquetes de Node si cambió package-lock.json
#   - recompila la interfaz si cambió algún archivo de frontend/ (por ejemplo, después de un git pull)
# Para cerrar la aplicación: Ctrl+C en esta ventana, o cerrarla.

param(
    [int]$Puerto = 8000,
    [switch]$AccesoDirecto
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest es muy lento en PowerShell 5.1 con la barra de progreso

$Nombre    = 'files2md'
$Raiz      = Split-Path -Parent $PSScriptRoot
$Backend   = Join-Path $Raiz 'backend'
$Frontend  = Join-Path $Raiz 'frontend'
$Dist      = Join-Path $Frontend 'dist'
$EsWindows = $env:OS -eq 'Windows_NT'
$Venv      = Join-Path $Backend '.venv'
if ($EsWindows) { $Py = Join-Path $Venv 'Scripts\python.exe'; $Npm = 'npm.cmd' }
else            { $Py = Join-Path $Venv 'bin/python';         $Npm = 'npm' }
$Url = "http://127.0.0.1:$Puerto"

function Paso([string]$texto) { Write-Host "`n> $texto" -ForegroundColor Cyan }
function Falla([string]$texto) {
    Write-Host "`n[X] $texto" -ForegroundColor Red
    if ($EsWindows) { Read-Host 'Presiona Enter para cerrar' | Out-Null }
    exit 1
}
function Ejecutar([string]$programa, [string[]]$argumentos, [string]$carpeta, [string]$siFalla) {
    Push-Location $carpeta
    try { & $programa @argumentos } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { Falla $siFalla }
}
function Huella([string]$archivo) { (Get-FileHash $archivo -Algorithm SHA256).Hash }
function Responde {
    try { Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}

Write-Host "$Nombre" -ForegroundColor Cyan

# 0. ¿Ya está abierta? Entonces solo se abre el navegador.
if (Responde) {
    Write-Host "$Nombre ya está funcionando en $Url"
    Start-Process $Url
    exit 0
}

# 1. Requisitos del sistema
$Python = $null
foreach ($candidato in @('py', 'python', 'python3')) {
    if (Get-Command $candidato -ErrorAction SilentlyContinue) {
        & $candidato --version *> $null
        if ($LASTEXITCODE -eq 0) { $Python = $candidato; break }
    }
}
if (-not $Python) { Falla 'No encuentro Python 3.11 o superior. Instálalo desde https://www.python.org y vuelve a intentar.' }
if (-not (Get-Command $Npm -ErrorAction SilentlyContinue)) { Falla 'No encuentro Node.js. Instálalo desde https://nodejs.org (versión LTS) y vuelve a intentar.' }

# 2. Entorno de Python
if (-not (Test-Path $Py)) {
    Paso 'Creando el entorno de Python (solo la primera vez)'
    Ejecutar $Python @('-m', 'venv', $Venv) $Backend 'No se pudo crear el entorno de Python.'
}
$marcaPy = Join-Path $Venv '.instalado'
$huellaPy = Huella (Join-Path $Backend 'pyproject.toml')
if (-not (Test-Path $marcaPy) -or (Get-Content $marcaPy -Raw).Trim() -ne $huellaPy) {
    Paso 'Instalando dependencias de Python (la primera vez tarda unos minutos)'
    Ejecutar $Py @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-e', '.') $Backend 'Falló pip install. Revisa el mensaje de arriba.'
    Set-Content $marcaPy $huellaPy
}

# 3. Paquetes de Node
$modulos = Join-Path $Frontend 'node_modules'
$marcaNode = Join-Path $modulos '.instalado'
$huellaNode = Huella (Join-Path $Frontend 'package-lock.json')
if (-not (Test-Path $marcaNode) -or (Get-Content $marcaNode -Raw).Trim() -ne $huellaNode) {
    Paso 'Instalando paquetes de la interfaz'
    Ejecutar $Npm @('install', '--no-audit', '--no-fund') $Frontend 'Falló npm install. Revisa el mensaje de arriba.'
    Set-Content $marcaNode $huellaNode
}

# 4. Compilar la interfaz solo si cambió algo desde la última vez
$indice = Join-Path $Dist 'index.html'
$fuentes = @(Get-ChildItem -File -Recurse (Join-Path $Frontend 'src'), (Join-Path $Frontend 'public')) +
           @(Get-ChildItem -File $Frontend | Where-Object { $_.Name -in 'index.html', 'package.json', 'package-lock.json', 'vite.config.ts', 'tsconfig.json' })
$ultimoCambio = ($fuentes | Measure-Object LastWriteTime -Maximum).Maximum
if (-not (Test-Path $indice) -or (Get-Item $indice).LastWriteTime -lt $ultimoCambio) {
    Paso 'Compilando la interfaz'
    Ejecutar $Npm @('run', 'build') $Frontend 'No se pudo compilar la interfaz. Revisa el mensaje de arriba.'
}

# 5. Acceso directo (opcional)
if ($AccesoDirecto -and $EsWindows) {
    $escritorio = [Environment]::GetFolderPath('Desktop')
    $acceso = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $escritorio "$Nombre.lnk"))
    # Se abre a través de cmd.exe: Windows no deja anclar a la barra de tareas un acceso directo que apunta a un .bat
    $acceso.TargetPath = $env:ComSpec
    $acceso.Arguments = '/c "' + (Join-Path $Raiz 'iniciar.bat') + '"'
    $acceso.WorkingDirectory = $Raiz
    $icono = Join-Path $Frontend 'public\favicon.ico'
    if (Test-Path $icono) { $acceso.IconLocation = $icono }
    $acceso.Save()
    Write-Host "Acceso directo creado en el Escritorio: $Nombre"
}

# 6. Servidor: sirve la API y la interfaz compilada en el mismo puerto (no hace falta Vite)
Paso "Iniciando $Nombre en $Url"
$env:FILES2MD_FRONTEND_DIR = $Dist
$servidor = Start-Process -FilePath $Py -WorkingDirectory $Backend -NoNewWindow -PassThru `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$Puerto")

try {
    $listo = $false
    for ($i = 0; $i -lt 60 -and -not $listo; $i++) {
        if ($servidor.HasExited) { Falla "El servidor se cerró al arrancar. ¿Está ocupado el puerto ${Puerto}? Prueba: iniciar.bat -Puerto 9000" }
        Start-Sleep -Milliseconds 500
        $listo = Responde
    }
    if (-not $listo) { Falla 'El servidor no respondió en 30 segundos.' }

    Write-Host "`nListo. Se abrió $Url en tu navegador." -ForegroundColor Green
    Write-Host 'Deja esta ventana abierta mientras uses la aplicación. Para cerrarla: Ctrl+C o cierra la ventana.'
    Start-Process $Url
    $servidor.WaitForExit()
}
finally {
    if (-not $servidor.HasExited) { Stop-Process -Id $servidor.Id -Force -ErrorAction SilentlyContinue }
}
