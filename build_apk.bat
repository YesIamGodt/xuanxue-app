@echo off
REM 玄学互动 - 安卓 APK 构建脚本
REM 需要: Node.js, Android SDK, Java 17
REM 注意: 静态资源已预置修复，直接同步即可

echo ========================================
echo  玄学互动 APK 构建脚本
echo ========================================

REM 设置 Java 17 路径
set JAVA_HOME_XUANXUE=C:\Program Files\Java\jdk-17
if not exist "%JAVA_HOME_XUANXUE%\bin\java.exe" (
    echo [错误] 未找到 Java 17，请检查 JAVA_HOME_XUANXUE 路径
    pause
    exit /b 1
)
set JAVA_HOME=%JAVA_HOME_XUANXUE%
echo [OK] JAVA_HOME = %JAVA_HOME%

cd /d "%~dp0"
echo [OK] 项目目录 = %CD%

REM Step 1: 复制已修复的静态资源到 dist
echo.
echo [Step 1] 同步静态资源到 dist...
if not exist "dist" mkdir dist
if not exist "dist\assets" mkdir dist\assets
copy /Y static\assets\*.js dist\assets\ >nul
copy /Y static\assets\*.css dist\assets\ >nul
copy /Y static\assets\*.json dist\assets\ >nul
copy /Y static\assets\*.png dist\assets\ >nul
copy /Y static\index.html dist\ >nul
echo [OK] 静态资源已同步

REM Step 2: 同步到 Android
echo.
echo [Step 2] 同步到 Android...
call node node_modules\@capacitor\cli\bin\cap sync android
if errorlevel 1 (
    echo [错误] Capacitor 同步失败
    pause
    exit /b 1
)

REM Step 3: 构建 APK
echo.
echo [Step 3] 构建 APK（需要 JAVA_HOME）...
cd android
call gradlew.bat assembleDebug --no-daemon
if errorlevel 1 (
    echo [错误] APK 构建失败
    cd ..
    pause
    exit /b 1
)
cd ..

REM Step 4: 复制 APK
echo.
echo [Step 4] 复制 APK 到根目录...
forfiles /p android\app\build\outputs\apk\debug /m *.apk /c "cmd /c copy /Y @path \"玄学互动_v2.0.apk\"" >nul 2>&1
if not exist "玄学互动_v2.0.apk" (
    copy /Y android\app\build\outputs\apk\debug\app-debug.apk "玄学互动_v2.0.apk" >nul
)
echo [OK] APK 已生成: 玄学互动_v2.0.apk

echo.
echo ========================================
echo  构建完成！
echo ========================================
pause
