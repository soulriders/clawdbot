@echo off
echo Switching Moltbot to Codex (OpenAI OAuth)...
node scripts\switch-config.js codex
if %errorlevel% neq 0 (
    echo Failed to update configuration.
    pause
    exit /b %errorlevel%
)

echo Restarting Gateway...
clawdbot gateway restart
echo Done! Moltbot is now active in Codex mode.
