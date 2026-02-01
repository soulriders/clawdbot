@echo off
echo Switching Moltbot to Gemini (Cloud Mode)...
node scripts\switch-config.js gemini
if %errorlevel% neq 0 (
    echo Failed to update configuration.
    pause
    exit /b %errorlevel%
)
echo Restarting Gateway...
clawdbot gateway restart
echo Done! Moltbot is now active.
