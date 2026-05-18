@echo off
setlocal
cd /d "%~dp0"

set "LOCAL_JAVA_HOME=C:\Users\student\Desktop\jdk-25.0.3+9"
set "LOCAL_MAVEN_CMD=C:\Users\student\Desktop\apache-maven-3.9.15\bin\mvn.cmd"

if not defined JAVA_HOME (
  if exist "%LOCAL_JAVA_HOME%\bin\java.exe" set "JAVA_HOME=%LOCAL_JAVA_HOME%"
)

if exist "target\mc-xbox-0.0.1-SNAPSHOT.jar" (
  if defined JAVA_HOME (
    "%JAVA_HOME%\bin\java.exe" -jar "target\mc-xbox-0.0.1-SNAPSHOT.jar"
  ) else (
    java -jar "target\mc-xbox-0.0.1-SNAPSHOT.jar"
  )
  exit /b %errorlevel%
)

if exist "%LOCAL_MAVEN_CMD%" (
  if defined JAVA_HOME (
    echo Using JAVA_HOME=%JAVA_HOME%
  ) else (
    echo JAVA_HOME is not set. Maven may fail unless Java is configured.
  )
  call "%LOCAL_MAVEN_CMD%" spring-boot:run
  exit /b %errorlevel%
)

echo Maven was not found and the jar does not exist yet.
echo Install Maven or build the project once, then rerun this file.
pause
