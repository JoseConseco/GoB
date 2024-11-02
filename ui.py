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
from bpy.types import Operator
from bpy.app.translations import pgettext_iface as iface_
from . import geometry, utils, gob_import


icons = None
preview_collections = {}

def draw_goz_buttons(self, context):

    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)

        icons = preview_collections["main"]

        if utils.prefs().show_button_text:
            row.operator(operator="scene.gob_export_button", 
                         text="Export", 
                         emboss=True, 
                         icon_value=icons["GOZ_SEND"].icon_id)
            
            if gob_import.run_background_update:
                row.operator(operator="scene.gob_import", 
                             text=iface_("Import", None), 
                             emboss=True, 
                             depress=True, 
                             icon_value=icons["GOZ_SYNC_ENABLED"].icon_id).action = 'AUTO'
            else:
                row.operator(operator="scene.gob_import", 
                             text=iface_("Import", None), 
                             emboss=True, 
                             depress=False, 
                             icon_value=icons["GOZ_SYNC_DISABLED"].icon_id).action = 'AUTO'
            
            row.operator(operator="scene.gob_import", 
                         text="Manual", 
                         emboss=True, 
                         depress=False, 
                         icon='IMPORT').action = 'MANUAL'
       
        else:
            row.operator(operator="scene.gob_export_button",
                         text="", 
                         emboss=True, 
                         icon_value=icons["GOZ_SEND"].icon_id)
            
            if gob_import.run_background_update:
                row.operator(operator="scene.gob_import", 
                             text="", 
                             emboss=True, 
                             depress=True, 
                             icon_value=icons["GOZ_SYNC_ENABLED"].icon_id).action = 'AUTO'
            else:
                row.operator(operator="scene.gob_import", 
                             text="", 
                             emboss=True, 
                             depress=False, 
                             icon_value=icons["GOZ_SYNC_DISABLED"].icon_id).action = 'AUTO'
           
            row.operator(operator="scene.gob_import", 
                         text="", 
                         emboss=True, 
                         depress=False, 
                         icon='IMPORT').action = 'MANUAL'


class GoB_OT_export_button(Operator):
    bl_idname = "scene.gob_export_button"
    bl_label = "Export to ZBrush"
    bl_description = "Export selected Objects to ZBrush\n"\
                        "LeftMouse: as Subtool\n"\
                        "SHIFT/CTRL/ALT + LeftMouse: as Tool"
    bl_options = {'INTERNAL'}
    
    @classmethod
    def poll(cls, context):              
        return geometry.export_poll(cls, context)
        #return bpy.context.selected_objects

    def invoke(self, context, event):
        as_tool = event.shift or event.ctrl or event.alt
        bpy.ops.scene.gob_export(as_tool=as_tool)
        return {'FINISHED'}
    

class GOB_OT_Popup(Operator):
    bl_label = "GoB: Zbrush Path not found!"
    bl_description ="look for zbrush in specified path or in default installation"\
                    "directories and if its not found prompt the user to input the path manually"
    bl_idname = "gob.search_zbrush"
          
    def draw(self, context):        
        self.layout.label(text='Please set your ZBrush path', icon='COLORSET_01_VEC')
        self.layout.label(text='        in the Add-ons Preferences')

    def open_addon_prefs(self, context):
        context.window_manager.addon_support = {'OFFICIAL', 'COMMUNITY', 'TESTING'}
        bpy.ops.preferences.addon_show(module=__package__)

    def invoke(self, context, event):       
        wm = context.window_manager
        if bpy.app.version < (4,3,0): 
            font_size_correction = bpy.context.preferences.ui_styles[0].widget_label.points / 10
        else:
            font_size_correction = bpy.context.preferences.ui_styles[0].tooltip.points / 10

        return wm.invoke_props_dialog(self, width = int(200 * font_size_correction))

    def execute(self, context):
        self.open_addon_prefs(context)
        return {'FINISHED'}


def ShowReport(self, message = [], title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        for i in message:
            self.layout.label(text=i)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


