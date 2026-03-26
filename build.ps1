$ErrorActionPreference = "Stop"

Write-Host "Compiling FFmpeg Studio into a standalone executable..."

# Use pyinstaller with custom bundled resource (the ffmpeg zip content we downloaded)
# --add-data syntax needs to be "src;dest" on Windows.
pyinstaller --onefile --noconsole --name "FFmpegStudio" --icon="icon.ico" --add-data "icon.ico;." --add-data "ffmpeg\bin\ffmpeg.exe;." app.py

Write-Host "Build complete! Check the dist folder for FFmpegStudio.exe"
