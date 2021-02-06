
import bpy 
import os 
from bpy.props import StringProperty, BoolProperty 
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.types import Operator 


class OT_OpenMyFilebrowser(Operator, ExportHelper): 
    bl_idname = "test.open_filebrowser" 
    bl_label = "Open the file browser (yay)" 
    
    def execute(self, context): 
        """Do something with the selected file(s).""" 
        return {'FINISHED'}



class OT_TestOpenFilebrowser(Operator, ExportHelper): 
    bl_idname = "test.open_filebrowser" 
    bl_label = "Open the file browser (yay)" 
    
    filter_glob: StringProperty( 
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp', 
        options={'HIDDEN'} ) 
        
    some_boolean: BoolProperty(
        name='Do a thing', 
        description='Do a thing with the file you\'ve selected', 
        default=True, ) 
        
    def execute(self, context): 
        """Do something with the selected file(s).""" 
        filename, extension = os.path.splitext(self.filepath)
        print('Selected file:', self.filepath) 
        print('File name:', filename) 
        print('File extension:', extension) 
        print('Some Boolean:', self.some_boolean) 
        return {'FINISHED'} 


    
# test call 
bpy.ops.test.open_filebrowser('INVOKE_DEFAULT')