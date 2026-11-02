<#
  Atalhos para Windows (PowerShell), equivalentes ao Makefile.
  Uso:  .\scripts\tasks.ps1 demo
        .\scripts\tasks.ps1 ingest
        .\scripts\tasks.ps1 build
        .\scripts\tasks.ps1 dashboard
#>
param([Parameter(Position = 0)][string]$Task = "help")

$Root = Split-Path -Parent $PSScriptRoot
# O caminho do banco vem do .env (DUCKDB_PATH) e é aplicado igualmente ao pipeline, ao dbt e ao
# dashboard — `malpipe dbt` repassa o caminho para o dbt.

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
    "build"     { Invoke-Dbt @("build"); malpipe recommend; malpipe publish }
    "publish"   { malpipe publish }
    "dbt-docs"  { Invoke-Dbt @("docs", "generate"); Invoke-Dbt @("docs", "serve", "--port", "8081") }
    "recommend" { malpipe recommend }
    "dashboard" { streamlit run (Join-Path $Root "dashboard\app.py") }
    "test"      { pytest }
    "status"    { malpipe status }
    default {
        Write-Host "Tarefas: install, demo, ingest, build, publish, dbt-docs, recommend, dashboard, test, status"
    }
}
