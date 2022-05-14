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

if "bpy" in locals():
    import importlib
    importlib.reload(GoB)
    importlib.reload(addon_updater)
else:
    from . import GoB
    from . import addon_updater
    
"""Addon preferences"""
import bpy
import os
from bpy.types import AddonPreferences
from bpy.props import ( StringProperty, 
                        BoolProperty, 
                        FloatProperty,
                        EnumProperty)


preferences_tabs = [
                    ("OPTIONS", "Options", ""),
                    ("IMPORT", "Import", ""),
                    ("EXPORT", "Export", ""),
                    ("UPDATE", "Update", ""),
                    ("HELP", "Troubleshooting", "")
                    ]

class GoB_Preferences(AddonPreferences):
    bl_idname = __package__

    
    tabs: EnumProperty(name="Tabs", items=preferences_tabs, default="OPTIONS")  

    #       ADDON UPDATER    
    repository_path: StringProperty(
        name="Project", 
        description="Github Project url example: https://github.com/JoseConseco/GoB", 
        subtype='DIR_PATH',
        default="https://github.com/JoseConseco/GoB") 
    
    zip_filename: StringProperty(
        name="zip_filename", 
        description="zip_filename", 
        subtype='FILE_PATH',
        default="blender_addon_updater.zip") 

    auto_update_check: BoolProperty(
        name="Check for updates automatically",
        description="auto_update_check",
        default=False)

    experimental_versions: BoolProperty(
        name="Experimental Versions",
        description="Check for experimental versions",
        default=False)
    ############################################

    #GLOBAL
    zbrush_exec: StringProperty(
        name="ZBrush Path", 
        description="Select Zbrush executable (C:\Program Files\Pixologic\ZBrush\ZBrush.exe). "
                    "\nIf not specified the system default for Zscript (.zsc) files will be used", 
        subtype='FILE_PATH',
        default="") 

    custom_pixologoc_path: BoolProperty(
        name="Custom Pixologic Public Path",
        description="This will allow you to set a custom Public Pixologic Path, this is where ZBrush stores GoZ configurations",
        default=False)

    import platform
    if platform.system() == 'Windows':
        PATH_GOZ = os.path.join(os.environ['PUBLIC'] , "Pixologic\\")
    elif platform.system() == 'Darwin': #osx
        PATH_GOZ = os.path.join("/Users/Shared/Pixologic")
    else:
        PATH_GOZ = False

    pixologoc_path: StringProperty(
        name="Pixologic Public Path", 
        description="Set public pixologic path, this needs to be a valid folder which zbrush accesses." 
                    "By default this folder is on the windows system drive under C:\\Users\\Public\\Pixologic", 
        subtype='DIR_PATH',
        default=PATH_GOZ)   

    project_path: StringProperty(
        name="Project Path", 
        description="Folder where Zbrush and Blender will store the exported content", 
        subtype='DIR_PATH',
        default=os.path.join(f"{GoB.PATH_GOZ}/GoZProjects/Default/"))
    
    clean_project_path: BoolProperty(
        name="Clean Project Files",
        description="Removes files in the project path to keep your GoZ bridge clean and your SSD happy",
        default=False)

    use_scale: EnumProperty(
            name="Scale",
            description="Create Material",
            items=[('MANUAL', 'Manual', 'Use Manual Factor for Scaling'),
                   ('BUNITS', 'Blender Units', 'Changes Scale depending on Blenders Unit Scale '),
                   ('ZUNITS', 'ZBrush Units', 'Scale single Object to ZBrush Units'),
                   ],
            default='BUNITS')  
    zbrush_scale: FloatProperty(
        name="ZBrush Scale",
        description="Target ZBrush Scale",
        default=2.0,
        min = 0.1,
        soft_max=10,
        step=1.0,
        precision=1,
        subtype='FACTOR') 
    manual_scale: FloatProperty(
        name="Scale Factor",
        description="Change Scale in Zbrush",
        default=1.0,
        min = 0.1,
        soft_max=10,
        step=1.0,
        precision=1,
        subtype='FACTOR') 
    flip_up_axis: BoolProperty(
        name="Flip up axis",
        description="Flip the up axis on Import/Export",
        default=False)
    flip_forward_axis: BoolProperty(
        name="Flip forward axis",
        description="Flip the forward axis on Import/Export",
        default=False)
    show_button_text: BoolProperty(
        name="Show Buttons Text",
        description="Show Text on the Import/Export Buttons",
        default=True)        
    performance_profiling: BoolProperty(
        name="[Dev] Debug performance",
        description="Show timing output in console, note this will slow down the GoZ transfer if enabled!",
        default=False)        
    debug_output: BoolProperty(
        name="[Dev] debug_output",
        description="Show debug output in console, note this will slow down the GoZ transfer if enabled!",
        default=False)
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
        items=[('APPLY_EXPORT', 'Export and Apply', 'Apply Modifiers in Blender and Export them to ZBrush'),
               ('ONLY_EXPORT', 'Only Export', 'Export Modifiers to ZBrush but do not apply them in Blender'),
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
    export_clear_mask: BoolProperty(
        name="Clear Mask",
        description="When enabled Masks will not be exported an cleared in ZBrush",
        default=False)
        
    export_remove_internal_faces: BoolProperty(
        name="Delete non manifold faces",
        description="Delete non manifold faces",
        default=True)

    export_merge: BoolProperty(
        name="Merge Vertices of Curves, Surfaces, Fonts and Meta Objects",
        description="Merges vertices of mesh type 'SURFACE', 'CURVE', 'FONT', 'META' that are in a given distance to each other",
        default=True)

    export_merge_distance: FloatProperty(
        name="Vertex Merge Threshold",
        description="Vertex Merge Threshold",
        default=0.0001,
        soft_min=0.0001,
        soft_max=0.01,
        step=0.0001,
        precision=4,
        subtype='DISTANCE') 



    # IMPORT
    import_timer: FloatProperty(
        name="Update interval",
        description="Interval (in seconds) to look for changes in GoZ_ObjectList.txt",
        default=0.5,
        min = 0.1,
        soft_max=2.0,
        step=0.1,
        precision=1,
        subtype='FACTOR') 
    import_material: EnumProperty(
            name="Material",
            description="Create Material",
            items=[('TEXTURES', 'from Textures', 'Create Material inputs from Textures'),        #TODO: fix export to zbrush
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
        default=False) 
    import_mask: BoolProperty(
        name="Mask",
        description="Import Mask to Vertex Group",
        default=True)
    import_uv: BoolProperty(
        name="UV Map",
        description="Import Uv Map from ZBrush",
        default=True) 
    import_uv_name: StringProperty(
        name="UV Map", 
        description="Set name for the UV Map", 
        default="UVMap")

    import_diffuse_suffix: StringProperty(
        name="Base Color", 
        description="Set Suffix for Base Color Map", 
        default="_diff")   
    import_diffuse_colorspace: EnumProperty(
        name="",
        description="diffuse_colorspace",
        items=[('Filmic Log', 'Filmic Log', 'Log based filmic shaper with 16.5 stops of latitude, and 25 stops of dynamic range'),
                ('Linear', 'Linear', 'Rec. 709 (Full Range), Blender native linear space'),
                ('Linear ACES', 'Linear ACES', 'ACES linear space'),
                ('Non-Color', 'Non-Color', 'Color space used for images which contains non-color data (i,e, normal maps)'),
                ('Raw', 'Raw', 'Raw'),
                ('sRGB', 'sRGB ', 'Standard RGB Display Space'),
                ('XYZ', 'XYZ ', 'XYZ'),
                ],
        default='sRGB')  
        
    import_displace_suffix: StringProperty(
        name="Displacement Map", 
        description="Set Suffix for Displacement Map", 
        default="_disp")    
    import_displace_colorspace: EnumProperty(
        name="",
        description="displace_colorspace",
        items=[('Filmic Log', 'Filmic Log', 'Log based filmic shaper with 16.5 stops of latitude, and 25 stops of dynamic range'),
                ('Linear', 'Linear', 'Rec. 709 (Full Range), Blender native linear space'),
                ('Linear ACES', 'Linear ACES', 'ACES linear space'),
                ('Non-Color', 'Non-Color', 'Color space used for images which contains non-color data (i,e, normal maps)'),
                ('Raw', 'Raw', 'Raw'),
                ('sRGB', 'sRGB ', 'Standard RGB Display Space'),
                ('XYZ', 'XYZ ', 'XYZ'),
                ],
        default='Linear')  

    import_normal_suffix: StringProperty(
        name="Normal Map", 
        description="Set Suffix for Normal Map", 
        default="_norm")        
    import_normal_colorspace: EnumProperty(
        name="",
        description="normal_colorspace",
        items=[('Filmic Log', 'Filmic Log', 'Log based filmic shaper with 16.5 stops of latitude, and 25 stops of dynamic range'),
                ('Linear', 'Linear', 'Rec. 709 (Full Range), Blender native linear space'),
                ('Linear ACES', 'Linear ACES', 'ACES linear space'),
                ('Non-Color', 'Non-Color', 'Color space used for images which contains non-color data (i,e, normal maps)'),
                ('Raw', 'Raw', 'Raw'),
                ('sRGB', 'sRGB ', 'Standard RGB Display Space'),
                ('XYZ', 'XYZ ', 'XYZ'),
                ],
        default='Non-Color')   
    

    def draw_options(self, box):
        # GoB General Options 
        box.use_property_split = True
        box.label(text='GoB General Options', icon='PREFERENCES') 
        col = box.column(align=True) 
        col.prop(self, 'zbrush_exec')
        col.prop(self, 'project_path') 

        col.prop(self, 'custom_pixologoc_path')
        if self.custom_pixologoc_path:
            col.prop(self, 'pixologoc_path')

        col.prop(self, 'clean_project_path')    
        col.prop(self, 'flip_up_axis')
        col.prop(self, 'flip_forward_axis')   
        col.prop(self, 'use_scale')
        if self.use_scale == 'MANUAL':                   
            col.prop(self, 'manual_scale')
        if self.use_scale == 'ZUNITS':                   
            col.prop(self, 'zbrush_scale')
        col.prop(self, 'show_button_text')  
        col.prop(self, 'performance_profiling')
        col.prop(self, 'debug_output')
        #col.prop(self, 'texture_format')
        

    def draw_import(self, box):
        # GoB Import Options
        box.use_property_split = True
        #box = layout.box() 
        box.label(text='GoB Import Options', icon='IMPORT')  
        col = box.column(align=True) 
        #box.prop(self, 'import_method')            #TODO: disabled: some bugs when switching
        col.prop(self, 'import_timer')           #TODO: disabled: some bugs when switching
        col.prop(self, 'import_material')  
        #col = box.column(align=True)  #TODO: add heading ="" in 2.9
        col.prop(self, 'import_mask')
        col.prop(self, 'import_uv')
        col.prop(self, 'import_polypaint')       
        col.prop(self, 'import_polygroups_to_vertexgroups')
        col.prop(self, 'import_polygroups_to_facemaps')          
        #col.prop(self, 'apply_facemaps_to_facesets')
        
        row = box.row(align=True)  
        row.prop(self, 'import_diffuse_suffix') 
        row.prop(self, 'import_diffuse_colorspace') 
        row = box.row(align=True)
        row.prop(self, 'import_normal_suffix')
        row.prop(self, 'import_normal_colorspace')       
        row = box.row(align=True)
        row.prop(self, 'import_displace_suffix') 
        row.prop(self, 'import_displace_colorspace')

        col = box.column(align=True) 
        col.prop(self, 'import_uv_name') 
        col.prop(self, 'import_polypaint_name') 

        

    def draw_export(self, box):
        # GoB Export Options
        box.use_property_split = True
        box.label(text='GoB Export Options', icon='EXPORT')   
        col = box.column(align=True) 
        col.prop(self, 'export_modifiers')
        col.prop(self, 'export_polygroups')    
        if self.export_polygroups == 'VERTEX_GROUPS':  
            col.prop(self, 'export_weight_threshold')
        col.prop(self, 'export_clear_mask') 
        
        col.prop(self, 'export_merge') 
        if self.export_merge:
            col.prop(self, 'export_merge_distance') 
        col.prop(self, 'export_remove_internal_faces')         
        
        
        

    def draw_help(self, box):
        # GoB Troubleshooting
        box.use_property_split = True
        #box = layout.box() 
        box.label(text='GoB Troubleshooting', icon='QUESTION')   
        import platform
        if platform.system() == 'Windows':
            icons = GoB.preview_collections["main"]  
            box.operator( "gob.install_goz", text="Install GoZ", icon_value=icons["GOZ_SEND"].icon_id ) 
            
        

        

    def draw_update(self, box):
        box.use_property_split = True
        box.label(text='Addon Updater', icon='PREFERENCES')  
        col  = box.column(align=False) 
        row  = col.row(align=False)         
        
        row.operator("au.check_updates", text="Check for Updates", icon='ERROR', depress=False).button_input = 0
        if addon_updater.update_available == False:
            row.operator("au.check_updates", text="Addon is up to date", icon='IMPORT', emboss=True, depress=True).button_input = -1
        elif addon_updater.update_available == None:
            row.operator("au.check_updates", text="nothing to show", icon='ERROR', emboss=False, depress=True).button_input = -1
        elif addon_updater.update_available == 'TIME':
            row.operator("au.check_updates", text="Limit exceeded! Try again later", icon='COLORSET_01_VEC', emboss=False, depress=True).button_input = -1
        else:
            row.operator("au.check_updates", text="Download: " + addon_updater.update_available, icon='COLORSET_03_VEC').button_input = 1
        
        col  = box.column(align=False)              
        col.prop(self, 'repository_path') 
        #col.prop(self, 'zip_filename')
        col.prop(self, 'experimental_versions') 
        #col.prop(self, 'auto_update_check')


    def draw(self, context):
        
        layout = self.layout
        # TAB BAR
        layout.use_property_split = False
        column = layout.column(align=True)
        row = column.row()
        row.prop(self, "tabs", expand=True)
        box = column.box()
        if self.tabs == "OPTIONS":
            self.draw_options(box)
        elif self.tabs == "EXPORT":
            self.draw_export(box)
        elif self.tabs == "IMPORT":
            self.draw_import(box)
        elif self.tabs == "HELP":
            self.draw_help(box)
        elif self.tabs == "UPDATE":
            self.draw_update(box)

        


 
