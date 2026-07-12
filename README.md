# GoB

GoZ-alike tools for simple ZBrush<->Blender interchange.

This is a fork of [JoseConseco/GoB](https://github.com/JoseConseco/GoB). Upstream docs and the wiki live there; this repo carries additional import fixes and improvements.

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

## Fork changes

Import reliability fixes on top of upstream:

* **View layer re-linking** — Re-importing an object that already exists in the `.blend` but is not on the active view layer (orphaned or in an excluded collection) no longer crashes on `select_set()`. The importer re-links the object into the scene collection and view layer before selecting it.
* **Low-poly name resolution** — ZBrush `_low2` / `_low3` object names are mapped onto the canonical Blender `_low` mesh when present.
* **Collection sync** — Imported `_low` meshes are linked into the same collections as their matching `_high` object.
* **Stale variant cleanup** — Duplicate numbered low variants (for example `_low2`, `_low.001`) are removed after resolving to the canonical `_low` object.
* **Face set safety** — Polygroup / face-set data is trimmed or padded to match the imported face count when counts diverge.

## GoB Setup
1. Download the latest **Source code (zip)** from [Releases](https://github.com/combwizard/GoB/releases), or use **Code → Download ZIP** on the branch you want to install.
2. Open Blender and navigate to **Edit → Preferences → Get Extensions**.
3. Uninstall any previous version of GoB by locating it in your extensions list, opening the drop-down menu on the right, and clicking **Uninstall**.
4. Install GoB by clicking the drop-down menu in the top right of the extensions window and selecting **Install from Disk**.
5. Select the zip file downloaded in step 1.
6. Locate GoB under **Edit → Preferences → Add-ons** to configure your settings.

## Usage
The addon adds three buttons to the top info panel:

* **Export** — Export the selected mesh objects to ZBrush.
* **Import** — Toggle autoloading mode. Models exported from ZBrush via GoZ are loaded into Blender automatically while this mode is on.
* **Manual** — Run a one-time import of the most recent model exported from ZBrush via GoZ.

## Acknowledgements
This script was originally written by user "Stunton" and posted [here on ZBrushCentral](http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender).

It was also [posted on Blender's wiki](https://en.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export) in the Import/Export Addons category, with the author listed as "ODe".

Maintained upstream by JoseConseco, Daniel Grauer (kromar), and contributors. Fork maintained by [combwizard](https://github.com/combwizard).
