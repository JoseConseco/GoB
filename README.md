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

## Clean Installation of GoB
1. Remove your old GoB addon from your Blender Addons Folder if you have one sitting there.
2. Install the zip via Preferences -> Add-ons -> Install from Disk (arrow top right corner).
3. Start Blender and enable the GoB addon in the Preferences > Addons menu and safe your preferences
4. Select a object you want to send to Zbrush and press the Export Button in the Header. 
   This will configure Zbrush to know that it is communicating with Blender, Run Zbrush and load in your Object.
5. Restart Zbrush and that is it.

## Usage
The addon adds two icons Import/Export to the top info panel:
* By clicking on the Export icon, you export the selected mesh objects into ZBrush.
* By clicking on the Import icon, you enable  autoloading mode. Latest objects are imported from GoZ.

# Acknowledgements
This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".
