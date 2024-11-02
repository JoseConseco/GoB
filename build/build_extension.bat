
rem Blender
rem BLENDER_DIR="C:\SteamLibrary\steamapps\common\Blender\blender.exe"
SET BLENDER_DIR="C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"

rem build folders
SET SOURCE_DIR=.\..\
SET OUTPUT_DIR=.\

rem blender --command extension build [-h] 
rem                                  [--source-dir SOURCE_DIR]
rem                                  [--output-dir OUTPUT_DIR]
rem                                  [--output-filepath OUTPUT_FILEPATH]
rem                                  [--valid-tags VALID_TAGS_JSON]
rem                                  [--split-platforms] [--verbose]

%BLENDER_DIR% -b --factory-startup --command extension build --source-dir %SOURCE_DIR% --output-dir %OUTPUT_DIR%

pause
