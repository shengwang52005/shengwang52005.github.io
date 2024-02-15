@echo off
git add .
set /p commit=Commit message...
echo Commit message:%commit%
echo ====================
git commit -m "%commit%"
echo ====================
echo Are you sure?
pause
echo ====================
git push origin main
echo ====================
echo Done!
pause
echo ====================
exit