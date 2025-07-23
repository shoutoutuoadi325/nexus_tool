@echo off
echo ========================================
echo   Nexus Repository 工具安装脚本
echo ========================================
echo.

echo 正在安装Python依赖包...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ 依赖安装失败！请检查：
    echo   1. Python是否已正确安装
    echo   2. pip是否可用
    echo   3. 网络连接是否正常
    pause
    exit /b 1
)

echo.
echo ✅ 依赖安装完成！
echo.
echo 接下来请运行配置助手设置Nexus服务器信息：
echo python setup_nexus.py
echo.
echo 或者直接编辑 refs\env_config.py 文件
echo.
echo 使用示例：
echo python nexus_cli.py --help
echo python nexus_demo.py
echo.
pause
