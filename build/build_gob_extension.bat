

rem Python
SET PYTHON_DIR=C:\Python310
set /p PYTHON_PATH="Enter your Python Path or press [ENTER] for default [%PYTHON_PATH%]: "
SET PATH=%PYTHON_PATH%;%PATH%

rem Blender
SET BLENDER_DIR=C:\SteamLibrary\steamapps\common\Blender\blender.exe

rem build folders
SET BUILD_DIR=Blender
SET SOURCE_DIR=.\..
SET OUTPUT_DIR=.\

rem blender --command extension build [-h] 
rem                                  [--source-dir SOURCE_DIR]
rem                                  [--output-dir OUTPUT_DIR]
rem                                  [--output-filepath OUTPUT_FILEPATH]
rem                                  [--valid-tags VALID_TAGS_JSON]
rem                                  [--split-platforms] [--verbose]

%BLENDER_DIR% --command extension build --source-dir %SOURCE_DIR% --output-dir %OUTPUT_DIR%

pause
