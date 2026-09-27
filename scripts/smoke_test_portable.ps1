$ErrorActionPreference = "Stop"

$port = 5011
$baseUrl = "http://127.0.0.1:$port"
$env:KEYSMITH_NO_BROWSER = "1"
$env:KEYSMITH_PORT = "$port"
$process = Start-Process -FilePath "dist\Keysmith.exe" -PassThru

try {
    $options = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $options = Invoke-RestMethod -Uri "$baseUrl/api/options"
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if ($null -eq $options -or -not $options.shutdown_available) {
        throw "The packaged Keysmith API did not start."
    }

    $search = @{
        target = "bitcoin"
        network = "mainnet"
        address_type = "p2pkh"
        match_mode = "prefix"
        pattern = "1"
        suffix_pattern = ""
        case_sensitive = $true
        workers = 1
    } | ConvertTo-Json

    Invoke-RestMethod `
        -Method Post `
        -Uri "$baseUrl/api/start" `
        -ContentType "application/json" `
        -Body $search | Out-Null

    $status = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $status = Invoke-RestMethod -Uri "$baseUrl/api/status"
        if ($status.status -eq "found") {
            break
        }
        if ($status.status -eq "error") {
            throw "The packaged worker failed: $($status.error)"
        }
        Start-Sleep -Milliseconds 500
    }

    if ($null -eq $status -or $status.status -ne "found") {
        throw "The packaged worker did not complete its smoke-test search."
    }

    Invoke-RestMethod `
        -Method Post `
        -Uri "$baseUrl/api/shutdown" `
        -Headers @{ "X-Keysmith-Shutdown" = $options.shutdown_token } | Out-Null

    if (-not $process.WaitForExit(10000)) {
        throw "The packaged Keysmith process did not shut down."
    }
    if ($process.ExitCode -ne 0) {
        throw "The packaged Keysmith process exited with code $($process.ExitCode)."
    }
} finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}
