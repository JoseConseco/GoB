# GoB

GoZ-alike tools for simple ZBrush<->Blender interchange.


## Features

You can transfer:
* Objects (only meshes)
* Polypainting
* UVs
* Mask
* Polygroup
* Diffuse map
* Normal map
* Displacement map



## Installation (updated)
1. Install the GoB addon for blender (follow steps from '**Configure Blender**') and activate.
1. Put the 'Blender' folder directly inside the _GoZApps_ folder at this path:
  * Windows: `C:/Users/Public/Pixologic/GoZApps`
  * Macintosh: `/Users/Shared/Pixologic/GoZApps`
2. re-install GoZ_for_ZBrush_Installer_WIN for Zbrush from here:
C:\Program Files\Pixologic\ZBrush 2019\Troubleshoot Help\GoZ_for_ZBrush_Installer_WIN.exe
3. launch ZBrush 2019.1 and run GoZ once and choose your blender install location.

### Configure Blender
**_Note**: If you have a previous version, remove it via the Addon panel (unroll the GoB entry and remove it) before continuing._

**_Note**: Github breaks (changes) name of zip file and the first (root) folder inside zip, when you download addon. Both zip file and first folder inside should be named: 'GoB'
The addon final location should look like this:
* C:\Users\XXXXX\AppData\Roaming\Blender Foundation\Blender\2.80\scripts\addons\**GoB**

1. In Blender, open the addon panel, then click the _'Install From Files...'_ button at the bottom. Select the `GoB.zip` file, this will install the addon inside the correct folder.
3. Check the **GoB** box and save the User preferences to launch it at startup. Then click on the Import icon on the header (on top of Blender) to activate autoloading.


## Usage

The addon adds two icons Import/Export to the top info panel:
* By clicking on the Export icon, you export the selected mesh objects into ZBrush.
* By clicking on the Import icon, you enable  autoloading mode. Latest objects are imported from GoZ.

## Known issues

* Blender can not have two objects with the same name, but ZBrush can. So if you export several objects from ZBrush, check names or some objects will be missed.

* Polygroups inside ZBrush use faces for grouping. Blender uses vertices for grouping, so the script does some conversion. There are some bugs with polygroups, so you might lose them...
* Same for polypainting, in Blender a vertex can have one color per face, but not in ZBrush.


# Acknowledgements

This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".
