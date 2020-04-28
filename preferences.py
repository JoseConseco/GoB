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

    polygroups: bpy.props.EnumProperty(
        name="Polygroups",
        description="Polygroups mode",
        items=[('MATERIALS', 'from Materials', 'Create Polygroups from Materials'),
               ('IGNORE', 'from Vertex Groups', 'Create Polygroups from Vertex Groups'),
               ],
        default='IGNORE')
    # ('FACEMAPS', 'from ** Face Maps', 'Create Polygroups from Face Maps'),


    export_scale_factor: bpy.props.FloatProperty(
        name="** Scale",
        description="export_scale_factor",
        default=1.0,
        min=0,
        soft_max=2,
        step=0.1,
        precision=2,
        subtype='FACTOR')


    # zbrush to blender
    shading: bpy.props.EnumProperty(
        name="Shading Mode",
        description="Shading mode",
        items=[('SHADE_SMOOTH', 'Smooth Shading', 'Objects will be Smooth Shaded after import'),
               ('SHADE_FLAT', 'Flat Shading', 'Objects will be Flat Shaded after import')
               ],
        default='SHADE_SMOOTH')

    materialinput: bpy.props.EnumProperty(
            name="Create material",
            description="choose source for material import",
            items=[#('TEXTURES', 'from Textures', 'Create mateial inputs from textures'),
                   ('POLYPAINT', 'from Polypaint', 'Create material inputs from polypaint'),
                   ('IGNORE', 'Ignore', 'No additional material inputs are created'),
                   ],
            default='IGNORE')

    polygroups_to_vertexgroups: bpy.props.BoolProperty(
        name="Polygroups as Vertex Groups",
        description="polygroups_to_vertexgroups",
        default=True)

    polygroups_to_facemaps: bpy.props.BoolProperty(
        name="Polygrous as Face Maps",
        description="polygroups_to_facemaps",
        default=True)

    apply_facemaps_to_facesets: bpy.props.BoolProperty(
        name="** apply_facemaps_to_facesets",
        description="apply_facemaps_to_facesets",
        default=True)

    switch_to_sculpt_mode: bpy.props.BoolProperty(
        name="** switch_to_sculpt_mode",
        description="switch_to_sculpt_mode",
        default=True)

    import_scale_factor: bpy.props.FloatProperty(
        name="** Scale",
        description="import_scale_factor",
        default=1.0, min=0, soft_max=2, step=0.1, precision=2,
        subtype='FACTOR')




    def draw(self, context):
        #GLOBAL OPTIONS
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'flip_up_axis')
        layout.prop(self, 'flip_forward_axis')
        layout.prop(self, 'show_button_text')
        col = layout.column()   # works best if a column, or even just self.layout

        #EXPORT OPTIONS
        box = layout.box()
        box.label(text='Export', icon='EXPORT')
        box.prop(self, 'export_scale_factor')
        box.prop(self, 'modifiers')
        box.prop(self, 'polygroups')


        # IMPORT OPTIONS
        box = layout.box()
        box.label(text='Import', icon='IMPORT')

        box.prop(self, 'import_scale_factor')
        box.prop(self, 'shading')
        box.prop(self, 'materialinput')
        box.prop(self, 'polygroups_to_vertexgroups')
        box.prop(self, 'polygroups_to_facemaps')
        box.prop(self, 'apply_facemaps_to_facesets')
        box.prop(self, 'switch_to_sculpt_mode')


