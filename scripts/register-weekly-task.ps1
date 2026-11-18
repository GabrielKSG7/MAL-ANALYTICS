<#
  Registra no Agendador de Tarefas do Windows a coleta semanal do MAL Analytics.

  Uso (PowerShell, na pasta do projeto, uma vez):
      .\scripts\register-weekly-task.ps1                 # domingo, 10:17
      .\scripts\register-weekly-task.ps1 -Day Saturday -At "09:43"
      .\scripts\register-weekly-task.ps1 -Remove         # desfaz

  A tarefa roda `tasks.ps1 weekly` (coleta + build) com o seu usuário, só quando você está logado.
  Se o computador estiver desligado no horário, ela roda assim que ele ligar. Logs em logs\.
#>
param(
    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$Day = "Sunday",
    [string]$At = "10:17",
    [switch]$Remove
)

$Name = "MAL Analytics - coleta semanal"
$Root = Split-Path -Parent $PSScriptRoot

if ($Remove) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarefa removida: $Name"
    return
}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Root\scripts\tasks.ps1`" weekly" `
    -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $At
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Coleta semanal (temporadas recentes + lista) e build do MAL Analytics" -Force | Out-Null

Write-Host "Agendado: $Name - toda $Day às $At."
Write-Host "Testar agora:  Start-ScheduledTask -TaskName '$Name'   (log em $Root\logs)"
