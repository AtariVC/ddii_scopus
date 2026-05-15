@echo off
chcp 65001 >nul

echo Добавление правила брандмауэра Windows для TCP 5012...

powershell -NoProfile -ExecutionPolicy Bypass -Command "New-NetFirewallRule -DisplayName 'ddii_tcp 5012 ZeroTier' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5012 -Profile Any"

echo.
echo Готово.
pause