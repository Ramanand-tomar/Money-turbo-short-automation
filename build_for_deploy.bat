@echo off
echo Installing dependencies for web-platform...
cd web-platform
call npm install
echo Building web-platform...
call npm run build
cd ..

echo Copying build files to resource\public...
if not exist "resource\public" mkdir "resource\public"
xcopy /E /I /Y "web-platform\dist\*" "resource\public\"

echo Done! The project is now ready for deployment.
