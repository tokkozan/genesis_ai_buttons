@echo off
cd /d "%~dp0"
echo Running Genesis in WSL2 Ubuntu-22.04 using the NVIDIA GPU.
echo Recording to outputs\replay\demo.mp4. First run may compile kernels.
wsl.exe -d Ubuntu-22.04 -- bash ./run_wsl.sh --record --output outputs/replay
if errorlevel 1 (
  echo Failed. Read the error above and README.md.
) else (
  echo Done. Open outputs\replay\demo.mp4
)
pause
