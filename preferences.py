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
from bpy.props import ( StringProperty, 
                        BoolProperty, 
                        FloatProperty,
                        PointerProperty,
                        EnumProperty)


class GoBPreferences(AddonPreferences):
    bl_idname = __package__

    #GLOBAL
    flip_up_axis: BoolProperty(
        name="Invert up axis",
        description="Enable this to invert the up axis on import/export",
        default=False)
    flip_forward_axis: BoolProperty(
        name="Invert forward axis",
        description="Enable this to invert the forward axis on import/export",
        default=False)
    show_button_text: BoolProperty(
        name="Show header buttons text",
        description="Enable this to show the import/export text of the header buttons",
        default=False)        
    performance_profiling: BoolProperty(
        name="[Debug] Process durations",
        description="This is used to identiyfy slow code, note this will slow down your transfer if enabled!",
        default=True)
    """      
    texture_format: EnumProperty(
        name="Image Format",
        description=" Output image format",
        items=[ ('TIFF', '.tif', ' Output image in TIFF format'), 
                ('BMP', '.bmp', ' Output image in BMP format'), 
                ('JPEG', '.jpg', ' Output image in JPEG format'), 
                ('PNG', '.png', ' Output image in PNG format'), 
               ],
        default='BMP')   
        """
    # EXPORT
    export_modifiers: EnumProperty(
        name='Modifiers',
        description='Modifiers Mode',
        items=[('APPLY_EXPORT', 'Export and Apply', 'Apply Modifiers in Blender and Export them to Zbrush'),
               ('ONLY_EXPORT', 'Only Export', 'Export Modifiers to Zbrush but do not apply them in Blender'),
               ('IGNORE', 'Ignore', 'Do not export modifiers')
               ],
        default='ONLY_EXPORT')
    export_polygroups: EnumProperty(
        name="Polygroups",
        description="Create Polygroups",
        items=[ ('FACE_MAPS', 'from Face Maps', 'Create Polygroups from Face Maps'), 
                #('MATERIALS', 'from Materials', 'Create Polygroups from Materials'),
                ('VERTEX_GROUPS', 'from Vertex Groups', 'Create Polygroups from Vertex Groups'),
                ('NONE', 'None', 'Do not Create Polygroups'),
               ],
        default='FACE_MAPS')  
    export_weight_threshold: FloatProperty(
        name="Weight Threshold",
        description="Only vertex weight higher than the threshold are converted to polygroups",
        default=0.1,
        min=0.01,
        max=1.0,
        step=0.01,
        precision=2,
        subtype='FACTOR') 
    export_scale_factor: FloatProperty(
        name="** Scale",
        description="export_scale_factor",
        default=1.0,
        min=0,
        soft_max=2,
        step=0.1,
        precision=2,
        subtype='FACTOR') 
    export_clear_mask: BoolProperty(
        name="Clear Mask",
        description="When enabled Masks will not be exported an cleared in Zbrush",
        default=False)


    # IMPORT
    import_material: EnumProperty(
            name="Material",
            description="Create Material",
            items=[#('TEXTURES', 'from Textures', 'Create Mateial inputs from Textures'),        #TODO: fix export to zbrush
                   ('POLYPAINT', 'from Polypaint', 'Create Material from Polypaint'),
                   ('NONE', 'None', 'No additional material inputs are created'),
                   ],
            default='POLYPAINT')            
    import_method: EnumProperty(
            name="Import Button Method",
            description="Manual Mode requires to press the import every time you send a model from zbrush to import it.",
            items=[('MANUAL', 'Manual', 'Manual Mode requires to press the import every time you send a model from zbrush to import it.'),
                   ('AUTOMATIC', 'Automatic', 'Automatic Mode'),
                   ],
            default='AUTOMATIC')
    import_scale_factor: FloatProperty(
        name="** Scale",
        description="import_scale_factor",
        default=1.0, min=0, soft_max=2, step=0.1, precision=2,
        subtype='FACTOR')
    import_polypaint: BoolProperty(
        name="Polypaint",
        description="Import Polypaint as Vertex Color",
        default=True) 
    import_polypaint_name: StringProperty(
        name="Vertex Color", 
        description="Set name for Vertex Color Layer", 
        default="Col")
    import_polygroups_to_vertexgroups: BoolProperty(
        name="Polygroups to Vertex Groups",
        description="Import Polygroups as Vertex Groups",
        default=False) 
    import_polygroups_to_facemaps: BoolProperty(
        name="Polygroups to Face Maps",
        description="Import Polygroups as Face Maps",
        default=True)
    apply_facemaps_to_facesets: BoolProperty(
        name="Apply Face Maps to Face Sets",
        description="apply_facemaps_to_facesets",
        default=True) 
    import_mask: BoolProperty(
        name="Mask",
        description="Import Mask to Vertex Group",
        default=True)
    import_uv: BoolProperty(
        name="UV Map",
        description="Import Uv Map from Zbrush",
        default=True) 
    import_uv_name: StringProperty(
        name="UV Map", 
        description="Set name for the UV Map", 
        default="UVMap")
    import_diffuse_suffix: StringProperty(
        name="Base Color", 
        description="Set Suffix for Base Color Map", 
        default="_diff")        
    import_displace_suffix: StringProperty(
        name="Displacement Map", 
        description="Set Suffix for Displacement Map", 
        default="_disp")
    import_normal_suffix: StringProperty(
        name="Normal Map", 
        description="Set Suffix for Normal Map", 
        default="_norm")
    
  
    def draw(self, context):
        #GLOBAL
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, 'flip_up_axis')
        layout.prop(self, 'flip_forward_axis')
        layout.prop(self, 'show_button_text')        
        layout.prop(self, 'performance_profiling') 
        #layout.prop(self, 'texture_format')

        #EXPORT
        col = layout.column()
        box = layout.box()
        box.label(text='Export', icon='EXPORT')  
        #box.prop(self, 'export_scale_factor')      #TODO
        box.prop(self, 'export_modifiers')
        box.prop(self, 'export_polygroups')    
        if self.export_polygroups == 'VERTEX_GROUPS':  
            box.prop(self, 'export_weight_threshold')
        box.prop(self, 'export_clear_mask') 
        
        # IMPORT
        col = layout.column(align=True)
        box = layout.box() 
        box.label(text='Import', icon='IMPORT')
        #box.prop(self, 'import_method')            #TODO: disabled: some bugs when switching
        #box.prop(self, 'import_scale_factor')      #TODO: add scaling
        box.prop(self, 'import_material')  
        col = box.column(align=True)  #TODO: add heading ="" in 2.9
        col.prop(self, 'import_mask')
        col.prop(self, 'import_uv')
        col.prop(self, 'import_polypaint')       
        col.prop(self, 'import_polygroups_to_vertexgroups')
        col.prop(self, 'import_polygroups_to_facemaps')          
        col.prop(self, 'apply_facemaps_to_facesets')
        
        col = box.column(align=True)  
        col.prop(self, 'import_diffuse_suffix') 
        col.prop(self, 'import_displace_suffix') 
        col.prop(self, 'import_normal_suffix')
        col = box.column(align=True) 
        col.prop(self, 'import_uv_name') 
        col.prop(self, 'import_polypaint_name') 


