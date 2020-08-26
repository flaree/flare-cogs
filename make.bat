@echo off

if [%1] == [] goto help

REM This allows us to expand variables at execution
setlocal ENABLEDELAYEDEXPANSION

REM This will set DIFF as a list of staged files
set DIFF=
for /F "tokens=* USEBACKQ" %%A in (`git diff --name-only --staged "*.py" "*.pyi"`) do (
    set DIFF=!DIFF! %%A
)

REM This will set DIFF as a list of files tracked by git
if [!DIFF!]==[] (
    set DIFF=
    for /F "tokens=* USEBACKQ" %%A in (`git ls-files "*.py" "*.pyi"`) do (
        set DIFF=!DIFF! %%A
    )
)

goto %1

:reformat
py -m autoflake --in-place --imports=aiohttp,discord,redbot !DIFF! || goto :eof
py -m isort !DIFF! || goto :eof
py -m black !DIFF!
goto :eof

:stylecheck
autoflake --check --imports aiohttp,discord,redbot !DIFF! || goto :eof
isort --check-only !DIFF! || goto :eof
black --check !DIFF!
goto :eof

:reformatblack
black !DIFF!
goto :eof


:help
echo Usage:
echo   make ^<command^>
echo.
echo Commands:
echo   reformat                   Reformat all .py files being tracked by git.
echo   stylecheck                 Check which tracked .py files need reformatting.
echo   newenv                     Create or replace this project's virtual environment.
echo   syncenv                    Sync this project's virtual environment to Red's latest
echo                              dependencies.
