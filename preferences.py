# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


"""Addon preferences"""
import bpy
from bpy.types import AddonPreferences
from . import addon_updater_ops


class GoBPreferences(AddonPreferences):
    bl_idname = __package__

    flip_up_axis: bpy.props.BoolProperty(
        name="Invert up axis",
        description="Enable this to invert the up axis on import/export",
        default=False)
    flip_forward_axis: bpy.props.BoolProperty(
        name="Invert forward axis",
        description="Enable this to invert the forward axis on import/export",
        default=False)
    show_button_text: bpy.props.BoolProperty(
        name="Show header buttons text",
        description="Enable this to show the import/export text of the header buttons",
        default=True)

    # blender to zbrush
    modifiers: bpy.props.EnumProperty(
        name='Modifiers',
        description='How to handle exported object modifiers',
        items=[('APPLY_EXPORT', 'Export and Apply', 'Apply modifiers to object and export them to zbrush'),
               ('ONLY_EXPORT', 'Only Export', 'Export modifiers to zbrush but do not apply them to mesh'),
               ('IGNORE', 'Ignore', 'Do not export modifiers')
               ],
        default='ONLY_EXPORT')


    # zbrush to blender
    shading: bpy.props.EnumProperty(
        name="Shading Mode",
        description="Shading mode",
        items=[('SHADE_SMOOTH', 'Smooth Shading', 'Objects will be Smooth Shaded after import'),
               ('SHADE_FLAT', 'Flat Shading', 'Objects will be Flat Shaded after import')
               ],
        default='SHADE_SMOOTH')

    polygroups: bpy.props.EnumProperty(
            name="Polygroups",
            description="Polygroups mode",
            items=[('MATERIALS', 'from Materials', 'Create Polygroups from Materials'),
                   ('IGNORE', 'Ignore', 'No additional polygroups are created'),
                   ],
            default='MATERIALS')

    materialinput: bpy.props.EnumProperty(
            name="Create material",
            description="choose source for material import",
            items=[#('TEXTURES', 'from Textures', 'Create mateial inputs from textures'),
                   ('POLYPAINT', 'from Polypaint', 'Create material inputs from polypaint'),
                   ('IGNORE', 'Ignore', 'No additional material inputs are created'),
                   ],
            default='IGNORE')

    # addon updater preferences
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'flip_up_axis')
        layout.prop(self, 'flip_forward_axis')
        layout.prop(self, 'show_button_text')
        col = layout.column()   # works best if a column, or even just self.layout


        box = layout.box()
        box.label(text='Blender to Zbrush', icon='EXPORT')
        box.prop(self, 'modifiers')


        box = layout.box()
        box.label(text='Zbrush to Blender', icon='IMPORT')
        box.prop(self, 'shading')
        box.prop(self, 'polygroups')
        box.prop(self, 'materialinput')

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)

