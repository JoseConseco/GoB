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
else:
    from . import GoB

import bpy
from . import addon_updater_ops

bl_info = {
    "name": "GoB",
    "description": "An unofficial GOZ-like for Blender",
    "author": "ODe",
    "version": (2, 0, 0),
    "blender": (2, 72, 0),
    "location": "At the info header",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions: 2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export",
    "tracker_url": "http://www.zbrushcentral.com/showthread.php?127419-GoB-an-unofficial-GoZ-for-Blender",
    "category": "Import-Export"}


class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # addon updater preferences

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31
    )
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23
    )
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59
    )

    def draw(self, context):
        layout = self.layout
        # col = layout.column() # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        #addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # col.operator("wm.url_open","Open webpage ").url=addon_updater_ops.updater.website


classes = (GoB.GoB_import,
           Preferences,
           GoB.GoB_export,
           GoB.INFO_HT_header,
           GoB.INFO_MT_editor_menus,
           GoB.GoB_ModalTimerOperator,
           )


def register():
    [bpy.utils.register_class(c) for c in classes]
    addon_updater_ops.register(bl_info)


def unregister():
    [bpy.utils.unregister_class(c) for c in classes]
