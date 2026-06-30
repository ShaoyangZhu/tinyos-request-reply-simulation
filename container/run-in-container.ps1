param(
    [string]$Scenario = "baseline",
    [string]$Image = "tinyos-request-reply:local",
    [string]$LogFile = "log.txt"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

docker build -t $Image $ProjectRoot
docker run --rm `
    -v "${ProjectRoot}:/app" `
    -w /app `
    -e "LOG_FILE=$LogFile" `
    $Image $Scenario
