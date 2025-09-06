# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import bpy
import os
import bpy.utils.previews
from . import (gob_import, 
               paths, 
               gob_export, 
               preferences, 
               ui)

bl_info = {
    "name": "GoB",
    "description": """GoB (for GoBlender) is an unofficial GoZ-like extension, providing a seamless bridge between ZBrush and Blender. 
          Effortlessly transfer your models between ZBrush and Blender with a single click, streamlining your workflow and maximizing efficiency.""",
    "author": "ODe, JoseConseco, Daniel Grauer (kromar)",
    "version": (4, 2, 3),
    "blender": (4, 00, 0),
    "location": "In the info header",
    "doc_url": "https://github.com/JoseConseco/GoB/wiki",                
    "tracker_url": "https://github.com/JoseConseco/GoB/issues/new",
    "category": "Import-Export"}


classes = (
    gob_import.GoB_OT_import,
    gob_export.GoB_OT_export,
    ui.GoB_OT_export_button,
    ui.GOB_OT_Popup,
    paths.GoB_OT_GoZ_Installer,
    preferences.GoB_Preferences,
    )


def register():
    [bpy.utils.register_class(c) for c in classes]

    global icons
    icons = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    icons.load("GOZ_SEND", os.path.join(icons_dir, "goz_send.png"), 'IMAGE')
    icons.load("GOZ_SYNC_ENABLED", os.path.join(icons_dir, "goz_sync_enabled.png"), 'IMAGE')
    icons.load("GOZ_SYNC_DISABLED", os.path.join(icons_dir, "goz_sync_disabled.png"), 'IMAGE')
    
    icons.load("GOZ_SEND_FLAT", os.path.join(icons_dir, "goz_send_flat.png"), 'IMAGE')
    icons.load("GOZ_SYNC_FLAT", os.path.join(icons_dir, "goz_sync_flat.png"), 'IMAGE')

    ui.preview_collections["main"] = icons 
    bpy.types.TOPBAR_HT_upper_bar.prepend(ui.draw_goz_buttons)


def unregister():

    for preferences.custom_icons in ui.preview_collections.values():
        bpy.utils.previews.remove(icons)
    ui.preview_collections.clear()

    bpy.types.TOPBAR_HT_upper_bar.remove(ui.draw_goz_buttons)

    [bpy.utils.unregister_class(c) for c in classes]

    if bpy.app.timers.is_registered(gob_import.run_import_periodically):
        bpy.app.timers.unregister(gob_import.run_import_periodically)
