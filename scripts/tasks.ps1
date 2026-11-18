<#
  Atalhos para Windows (PowerShell), equivalentes ao Makefile.
  Uso:  .\scripts\tasks.ps1 demo
        .\scripts\tasks.ps1 ingest
        .\scripts\tasks.ps1 weekly
        .\scripts\tasks.ps1 ecosystem
        .\scripts\tasks.ps1 build
        .\scripts\tasks.ps1 dashboard
#>
param([Parameter(Position = 0)][string]$Task = "help")

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
# Usa o venv do projeto mesmo sem ativá-lo (ex.: quando roda pelo Agendador de Tarefas).
$VenvScripts = Join-Path $Root ".venv\Scripts"
if ((Test-Path $VenvScripts) -and ($env:PATH -notlike "*$VenvScripts*")) { $env:PATH = "$VenvScripts;$env:PATH" }
# O caminho do banco vem do .env (DUCKDB_PATH) e é aplicado igualmente ao pipeline, ao dbt e ao
# dashboard - `malpipe dbt` repassa o caminho para o dbt.

function Invoke-Dbt([string[]]$DbtArgs) {
    malpipe dbt @DbtArgs
    if ($LASTEXITCODE -ne 0) { throw "dbt falhou" }
}

switch ($Task) {
    "install"   { pip install -e ".[dev,dashboard]" }
    "demo" {
        $env:DUCKDB_PATH = Join-Path $Root "data\demo.duckdb"
        malpipe sample
        Invoke-Dbt @("build")
        malpipe recommend --username demo_user
        Write-Host "Pronto. Para abrir o painel: `$env:DUCKDB_PATH='$env:DUCKDB_PATH'; streamlit run dashboard/app.py"
    }
    "ingest"    { malpipe incremental }
    "weekly" {
        # Coleta semanal (temporadas recentes + sua lista) e build completo, com log em logs\.
        $Logs = Join-Path $Root "logs"; New-Item -ItemType Directory -Force $Logs | Out-Null
        Start-Transcript -Path (Join-Path $Logs ("weekly-" + (Get-Date -Format "yyyy-MM-dd") + ".log")) -Append | Out-Null
        try {
            malpipe weekly
            if ($LASTEXITCODE -ne 0) { throw "malpipe weekly falhou" }
            Invoke-Dbt @("build"); malpipe recommend; malpipe publish; malpipe site
        } finally { Stop-Transcript | Out-Null }
    }
    "ecosystem" { malpipe check-sources; malpipe ecosystem }
    "sources"   { malpipe check-sources }
    "site"      { malpipe site; python scripts/check_site.py site }
    "preview"   { python -m http.server -d site 8000 }
    "build"     { Invoke-Dbt @("build"); malpipe recommend; malpipe publish; malpipe site }
    "publish"   { malpipe publish }
    "dbt-docs"  { Invoke-Dbt @("docs", "generate"); Invoke-Dbt @("docs", "serve", "--port", "8081") }
    "recommend" { malpipe recommend }
    "dashboard" { streamlit run (Join-Path $Root "dashboard\app.py") }
    "test"      { pytest }
    "status"    { malpipe status }
    default {
        Write-Host "Tarefas: install, demo, ingest, weekly, ecosystem, sources, site, preview, build, publish, dbt-docs, recommend, dashboard, test, status"
    }
}
