<#
  Atalhos para Windows (PowerShell), equivalentes ao Makefile.
  Uso:  .\scripts\tasks.ps1 demo
        .\scripts\tasks.ps1 ingest
        .\scripts\tasks.ps1 build
        .\scripts\tasks.ps1 dashboard
#>
param([Parameter(Position = 0)][string]$Task = "help")

$Root = Split-Path -Parent $PSScriptRoot
if (-not $env:DUCKDB_PATH) { $env:DUCKDB_PATH = Join-Path $Root "data\mal.duckdb" }
$env:DBT_PROFILES_DIR = Join-Path $Root "dbt"

function Invoke-Dbt([string[]]$DbtArgs) {
    Push-Location (Join-Path $Root "dbt")
    try { dbt @DbtArgs; if ($LASTEXITCODE -ne 0) { throw "dbt falhou" } } finally { Pop-Location }
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
    "build"     { Invoke-Dbt @("build"); malpipe recommend }
    "dbt-docs"  { Invoke-Dbt @("docs", "generate"); Invoke-Dbt @("docs", "serve", "--port", "8081") }
    "recommend" { malpipe recommend }
    "dashboard" { streamlit run (Join-Path $Root "dashboard\app.py") }
    "test"      { pytest }
    "status"    { malpipe status }
    default {
        Write-Host "Tarefas: install, demo, ingest, build, dbt-docs, recommend, dashboard, test, status"
    }
}
