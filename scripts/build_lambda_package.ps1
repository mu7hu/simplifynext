param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

$ErrorActionPreference = "Stop"
$package = Join-Path $ProjectRoot "lambda_package"
$requirements = Join-Path $ProjectRoot "requirements-lambda.txt"

if (Test-Path -LiteralPath $package) {
    Remove-Item -LiteralPath $package -Recurse -Force
}

New-Item -ItemType Directory -Path "$package\traction", "$package\data" -Force | Out-Null
Copy-Item -Path (Join-Path $ProjectRoot "src\traction\*") -Destination "$package\traction" -Recurse -Force
Copy-Item -Path (Join-Path $ProjectRoot "data\founder_briefs"), (Join-Path $ProjectRoot "data\example_profiles"), (Join-Path $ProjectRoot "data\benchmark_priors") -Destination "$package\data" -Recurse -Force

$root = (Resolve-Path $ProjectRoot).Path
docker run --rm --entrypoint /bin/sh `
    -v "${root}:/src" `
    -v "${package}:/var/task" `
    public.ecr.aws/lambda/python:3.12 `
    -c "pip install --no-cache-dir --ignore-installed -r /src/requirements-lambda.txt -t /var/task"

Write-Host "Lambda package created at $package"
