# GoB

GoZ-alike tools for simple ZBrush<->Blender interchange.

## Features
You can transfer:
* Objects (only meshes)
* Polypainting
* UVs
* Mask
* FaceSets
* Polygroup
* Diffuse map
* Normal map
* Displacement map

## GoB Setup
1. Download the latest "Source code (zip)" from "Releases"
2. Open Blender and Navigate to Edit > Preferences > Get Extensions
3. Uninstall any previous version of GoB by locating it in your extensions list, opening the drop down menu on the right side, and clicking "uninstall".
4. Install GoB by clicking the drop down menu found in the top right of the extensions window, and selecting "install from disk".
5. Navigate to and select the zip file downloaded in step One.
6. Locate GoB in Edit > Preferences > Add-ons to configure your settings.


## Usage
The addon adds two icons Import/Export to the top info panel:
* By clicking on the Export icon, you export the selected mesh objects into ZBrush.
* By clicking on the Import icon, you toggle autoloading mode. This will automatically load any models into blender that are exported from ZBrush via GoZ.
* By clicking on the Manual icon, you execute a one time import of the most recent model exported from ZBrush via GoZ.


# Acknowledgements
This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".
