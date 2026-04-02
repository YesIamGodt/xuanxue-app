@echo off
set ANDROID_HOME=C:\android-sdk
set JAVA_HOME=C:\Program Files\Java\jdk-17
set PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\cmdline-tools\latest\bin;%PATH%
echo y | avdmanager.bat create avd -n test_avd -k "system-images;android-34;google_apis;x86_64"
echo Done.
