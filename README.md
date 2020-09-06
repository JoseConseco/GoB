# GoB

GoZ-alike tools for simple ZBrush<->Blender interchange.

## Features
You can transfer:
* Objects (only meshes)
* Polypainting
* UVs
* Mask
* FaceMaps
* Polygroup
* Diffuse map
* Normal map
* Displacement map

## Clean Installation of GoB
1. Remove your old GoB addon from your Blender Addons Folder
2. Copy the extracted GoB addon into your Blender Addon Folder
3. Start Blender and enable the GoB addon in the Preferences > Addons menu and safe your preferences
4. Select a object you want to send to Zbrush and press the Export Button in the Header. 
   This will configure Zbrush to know that it is communicating with Blender, Run Zbrush and load in your Object.
5. Restart Zbrush and that is it.

## Update GoB
1. Remove your old GoB addon from your Blender Addons Folder
2. Copy the extracted GoB addon into your Blender Addon Folder


### Configure Blender
**_Note**: If you have a previous version, remove it via the Addon panel (unroll the GoB entry and remove it) before continuing._

**_Note**: Github breaks (changes) name of zip file and the first (root) folder inside zip, when you download addon. Both zip file and first folder inside should be named: 'GoB'
The addon final location sould look like this:
* C:\Users\XXXXX\AppData\Roaming\Blender Foundation\Blender\2.80\scripts\addons\**GoB**

1. In Blender, open the addon panel, then click the _'Install From Files...'_ button at the bottom. Select the `GoB.zip` file, this will install the addon inside the correct folder.
3. Check the **GoB** box and save the User preferences to launch it at startup. Then click on the Import icon on the header (on top of Blender) to activate autoloading.


## Usage
The addon adds two icons Import/Export to the top info panel:
* By clicking on the Export icon, you export the selected mesh objects into ZBrush.
* By clicking on the Import icon, you enable  autoloading mode. Latest objects are imported from GoZ.


# Acknowledgements
This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".
