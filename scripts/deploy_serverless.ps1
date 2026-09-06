param(
    [string]$Profile = "simplifynext",
    [string]$Region = "us-east-1",
    [string]$Stack = "simplifynext-dev"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sam = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"

& (Join-Path $PSScriptRoot "build_lambda_package.ps1") -ProjectRoot $root
& $sam validate --lint --template-file (Join-Path $root "template.yaml")
& $sam deploy --template-file (Join-Path $root "template.yaml") --config-env default --profile $Profile --region $Region --no-confirm-changeset
python (Join-Path $PSScriptRoot "upload_reference_data.py") --stack $Stack --profile $Profile --region $Region --project-root $root
