param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Command
)

wsl -d Ubuntu -- bash -lc "$Command"
exit $LASTEXITCODE
