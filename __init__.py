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

bl_info = {
    "name": "GoB",
    "description": "An unofficial GOZ-like for Blender",
    "author": "ODe",
    "version": (2, 80),
    "blender": (2, 80, 0),
    "location": "At the info header",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:"
                "2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export",
    "tracker_url": "http://www.zbrushcentral.com/showthread.php?"
                "127419-GoB-an-unofficial-GoZ-for-Blender",
    "category": "Import-Export"}


if "bpy" in locals():
    import importlib
    importlib.reload(GoB)
else:
    from . import GoB

import bpy



classes = (
    GoB.GoB_OT_import,
    GoB.GoB_OT_export,
    GoB.GoBPreferences,
    GoB.GoB_OT_ModalTimerOperator
    )


def register():
    [bpy.utils.register_class(c) for c in classes]
    bpy.types.TOPBAR_HT_upper_bar.append(GoB.draw_goz)


def unregister():
    [bpy.utils.unregister_class(c) for c in classes]
    bpy.types.TOPBAR_HT_upper_bar.remove(GoB.draw_goz)


