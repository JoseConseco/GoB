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


if "bpy" in locals():
    import importlib
    importlib.reload(GoB)
    importlib.reload(preferences)
else:
    from . import GoB
    from . import preferences

import bpy
import os
import bpy.utils.previews


bl_info = {
    "name": "GoB",
    "description": "An unofficial GOZ-like addon for Blender",
    "author": "ODe, JoseConseco, Daniel Grauer",
    "version": (3, 4, 13),
    "blender": (2, 83, 0),
    "location": "In the info header",
    "doc_url": "https://github.com/JoseConseco/GoB/wiki",                
    "tracker_url": "https://github.com/JoseConseco/GoB/issues/new",
    "category": "Import-Export"}


classes = (
    GoB.GoB_OT_import,
    GoB.GoB_OT_export,
    GoB.GoB_OT_OpenFilebrowser,
    preferences.GoBPreferences,
    )


def register():
    for c in classes:
        bpy.utils.register_class(c)

    global icons
    icons = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    icons.load("GOZ_SEND", os.path.join(icons_dir, "goz_send.png"), 'IMAGE')
    icons.load("GOZ_SYNC_ENABLED", os.path.join(icons_dir, "goz_sync_enabled.png"), 'IMAGE')
    icons.load("GOZ_SYNC_DISABLED", os.path.join(icons_dir, "goz_sync_disabled.png"), 'IMAGE')
    GoB.preview_collections["main"] = icons

    bpy.types.TOPBAR_HT_upper_bar.append(GoB.draw_goz_buttons)


def unregister():

    for preferences.custom_icons in GoB.preview_collections.values():
        bpy.utils.previews.remove(icons)
    GoB.preview_collections.clear()

    bpy.types.TOPBAR_HT_upper_bar.remove(GoB.draw_goz_buttons)

    [bpy.utils.unregister_class(c) for c in classes]

    if bpy.app.timers.is_registered(GoB.run_import_periodically):
        bpy.app.timers.unregister(GoB.run_import_periodically)
