@echo off
echo Switching Moltbot to LFM (Local Mode)...
node scripts\switch-config.js lfm
if %errorlevel% neq 0 (
    echo Failed to update configuration.
    pause
    exit /b %errorlevel%
)

echo Setting up network environment for Local Ollama...
set NO_PROXY=localhost,127.0.0.1,::1
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set OLLAMA_API_KEY=ollama-local

echo Restarting Gateway...
clawdbot gateway restart
echo Done! Moltbot is now active (Tools Disabled, Proxy Cleared).
