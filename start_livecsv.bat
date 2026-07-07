@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ---- 检测是否已有实例在运行（python.exe 运行 livecsv.py）----
rem ---- Check if an instance is already running (python.exe running livecsv.py) ----
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*livecsv.py*' }; if ($p) { exit 1 } else { exit 0 }"
if "%errorlevel%"=="1" (
    echo ========================================
    echo   LiveCSV 已在运行 / Already running
    echo ========================================
    echo.
    echo 如需打开界面，请从 LiveCSV 托盘菜单选择「打开 WebUI」。
    echo To open the UI, choose "Open WebUI" from the LiveCSV tray menu.
    echo.
    echo 按任意键关闭，或 3 秒后自动关闭...
    echo Press any key to close, or this window will close in 3 seconds...
    timeout /t 3 >nul
    exit /b 0
)

echo ========================================
echo   启动 LiveCSV / Starting LiveCSV
echo ========================================
echo.

rem 通过 VBS 静默启动 Python（无控制台窗口，立即返回）
rem Launch Python silently via VBS (no console window, returns immediately)
echo Set ws = CreateObject("WScript.Shell") > "%TEMP%\livecsv_start.vbs"
echo ws.Run "python ""%~dp0livecsv.py""", 0, False >> "%TEMP%\livecsv_start.vbs"
wscript "%TEMP%\livecsv_start.vbs"
del "%TEMP%\livecsv_start.vbs" 2>nul

echo 正在启动 LiveCSV 服务...
echo Starting LiveCSV service...
timeout /t 3 /nobreak >nul

echo LiveCSV 已在后台启动，浏览器将自动打开。
echo LiveCSV started in the background; the browser will open automatically.
echo.
echo 如需退出，请从 LiveCSV 托盘菜单选择「退出」。
echo To quit, choose "Quit" from the LiveCSV tray menu.
echo.
echo 按任意键关闭，或 5 秒后自动关闭...
echo Press any key to close, or this window will close in 5 seconds...
timeout /t 5 >nul
exit
