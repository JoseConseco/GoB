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


## Installation

First of all, GoZ for ZBrush must be installed!

### Configure Blender
_Note: If you have a previous version, remove it via the Addon panel (unroll the GoB entry and remove it) before continuing._

1. Extract the 'GoB_2-72.py' file somewhere outside of the zip file.
2. In Blender, open the addon panel, then click the _'Install From Files...'_ button at the bottom. Select the `GoB_2-72.py` file, this will install the addon inside the correct folder.
3. Check the **GoB** box and save the User preferences to launch it at startup. Then click on the blue icon on the header (on top of Blender) to activate autoloading. The icon is green for autoloading activated.

### Configure ZBrush
1. Put the 'Blender' folder directly inside the _GoZApps_ folder at this path:
  * Windows: `C:/Users/Public/Pixologic/GoZApps`
  * Macintosh: `/Users/Shared/Pixologic/GoZApps`
2. Launch ZBrush. In _'Preferences' -> 'GoZ'_, you should see the 'path to Blender' entry. This will create the config for Blender. Now you can select it to use GoZ with Blender. Check the GoZ manual to use it.


## Usage

The addon adds two icons (the Brush Pinch icon and a blue icon) to the top info panel:
* By clicking on the brush icon, you export the selected mesh objects into ZBrush.
* By clicking on the Blue icon, you switch it to green and activate the autoloading mode. Latest objects are imported from GoZ.

## Known issues

* Blender can not have two objects with the same name, but ZBrush can. So if you export several objects from ZBrush, check names or some objects will be missed.
* From Blender you need to manually apply modifiers before exporting objects, in example if you do not apply the mirror modifier, you will have only one side of your object in ZBrush)
* Polygroups inside ZBrush use faces for grouping. Blender uses vertices for grouping, so the script does some conversion. There are some bugs with polygroups, so you might lose them...
* Same for polypainting, in Blender a vertex can have one color per face, but not in ZBrush.


# Acknowledgements

This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".
