Set-Location "D:\Service\homeGallery"
$env:PYTHONIOENCODING = "utf-8"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 2>&1 | Out-File -Append data/startup.log
