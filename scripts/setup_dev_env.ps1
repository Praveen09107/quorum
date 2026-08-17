# setup_dev_env.ps1 — real, working local environment setup.

Write-Host "Setting up Quorum backend..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\..\backend"
pip install -e .
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend/.env from example — fill in real values as you get them." -ForegroundColor Yellow
}
Pop-Location

Write-Host "Setting up Quorum mobile..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\..\mobile"
flutter pub get
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created mobile/.env from example — fill in real values as you get them." -ForegroundColor Yellow
}
Pop-Location

Write-Host "`nDone. Run 'pytest tests -q' in backend/ and 'dart test' in mobile/ to confirm." -ForegroundColor Green