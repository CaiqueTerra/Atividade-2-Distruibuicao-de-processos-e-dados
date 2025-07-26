@echo off
echo ================================================
echo   CIDADE INTELIGENTE - INICIANDO GATEWAY
echo ================================================
echo.
echo 🏙️  Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado! Instale Python 3.8 ou superior.
    pause
    exit /b 1
)
echo.

echo 🔧 Verificando dependências...
echo    - Flask (servidor web)
echo    - grpcio (comunicação gRPC)  
echo    - pika (RabbitMQ)
echo.

echo 🚀 Iniciando Gateway...
echo    📱 Interface Web: http://localhost:5000
echo    🔗 Para parar: Ctrl+C
echo.
echo ================================================
echo.

cd /d "%~dp0"
python Gateway.py

echo.
echo ================================================
echo   Gateway finalizado
echo ================================================
pause
