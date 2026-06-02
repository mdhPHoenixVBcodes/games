@echo off
echo Starting File Transfer App...

set JAVA_HOME="C:\Users\student\Desktop\jdk-21"
set PATH=%JAVA_HOME%\bin;%PATH%
cd /d "C:\Users\student\Desktop\games\project-filetransfer"

C:\Users\student\Desktop\apache-maven-3.9.15\bin\mvn.cmd spring-boot:run

pause