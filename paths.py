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
import platform
from subprocess import Popen
from bpy.types import Operator
from . import ui, utils, gob_import


def gob_init_os_paths():   
    isMacOS = False
    useZSH = False
    if platform.system() == 'Windows':  
        print("GoB Found System: ", platform.system())
        isMacOS = False
        PATH_GOZ = os.path.join(os.environ['PUBLIC'] , "Pixologic")

    elif platform.system() == 'Darwin': #osx
        print("GoB Found System: ", platform.system())

        # with macOS Catalina (10.15) apple switched from bash to zsh as default shell
        if platform.mac_ver()[0] < str(10.15):
            print("use bash")
            useZSH = False
        else: 
            print("use zsh")
            useZSH = True

        isMacOS = True        
        #print(os.path.isfile("/Users/Shared/Pixologic/GoZBrush/GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"))
        PATH_GOZ = os.path.join("/Users/Shared/Pixologic")
    else:
        print("GoB Unkonwn System: ", platform.system())
        PATH_GOZ = False ## NOTE: GOZ seems to be missing, reinstall from zbrush
    
    PATH_GOB =  os.path.abspath(os.path.dirname(__file__))
    PATH_BLENDER = os.path.join(bpy.app.binary_path)    
    PATH_OBJLIST = os.path.join(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt")
    PATH_CONFIG = os.path.join(f"{PATH_GOZ}/GoZBrush/GoZ_Config.txt") 
    PATH_SCRIPT = os.path.join(f"{PATH_GOB}/ZScripts/GoB_Import.zsc")
    PATH_VARS = os.path.join(f"{PATH_GOZ}/GoZProjects/Default/GoB_variables.zvr")  

    return isMacOS, PATH_GOB, PATH_BLENDER, PATH_GOZ, PATH_OBJLIST, PATH_CONFIG, PATH_SCRIPT, PATH_VARS


#create GoB paths when loading the addon
isMacOS, PATH_GOB, PATH_BLENDER, PATH_GOZ, PATH_OBJLIST, PATH_CONFIG, PATH_SCRIPT, PATH_VARS = gob_init_os_paths()
#print("GoZ Paths: ", gob_init_os_paths())


def find_zbrush(self, context, isMacOS):
    #get the highest version of zbrush and use it as default zbrush to send to
    self.is_found = False 
    if utils.prefs().zbrush_exec:        
        #OSX .app files are considered packages and cant be recognized with path.isfile and needs a special condition
        if isMacOS:
            if os.path.isdir(utils.prefs().zbrush_exec) and 'zbrush.app' in str.lower(utils.prefs().zbrush_exec):
                self.is_found = True   

        else: #is PC
            if os.path.isfile(utils.prefs().zbrush_exec):  #validate if working file here    
                #check if path contains zbrush, that should identify a zbrush executable
                if 'zbrush.exe' in str.lower(utils.prefs().zbrush_exec): 
                    self.is_found = True

            elif os.path.isdir(utils.prefs().zbrush_exec): #search for zbrush files in this folder and its subfolders 
                for folder in os.listdir(utils.prefs().zbrush_exec): 
                    if "zbrush" in str.lower(folder):     #search for content inside folder that contains zbrush
                        #search subfolders for executables
                        if os.path.isdir(os.path.join(utils.prefs().zbrush_exec, folder)): 
                            i,zfolder = utils.max_list_value(os.listdir(os.path.join(utils.prefs().zbrush_exec)))
                            for file in os.listdir(os.path.join(utils.prefs().zbrush_exec, zfolder)):
                                if ('zbrush.exe' in str.lower(file) in str.lower(file)):            
                                    utils.prefs().zbrush_exec = os.path.join(utils.prefs().zbrush_exec, zfolder, file)           
                                    self.is_found = True   

                        #find executable
                        if os.path.isfile(os.path.join(utils.prefs().zbrush_exec,folder)) and ('zbrush.exe' in str.lower(folder) in str.lower(folder)):            
                            utils.prefs().zbrush_exec = os.path.join(utils.prefs().zbrush_exec, folder)           
                            self.is_found = True  

    else:    # the  applications default path can try if zbrush is installed in its defaut location  
        #look for zbrush in default installation path 
        if isMacOS:
            folder_List = []                 
            filepath = os.path.join(f"/Applications")
            if os.path.isdir(filepath):
                [folder_List.append(i) for i in os.listdir(filepath) if 'zbrush' in str.lower(i)]
                i, zfolder = utils.max_list_value(folder_List)
                utils.prefs().zbrush_exec = os.path.join(filepath, zfolder, 'ZBrush.app')
                ui.ShowReport(self, [utils.prefs().zbrush_exec], "GoB: Zbrush default installation found", 'COLORSET_03_VEC') 
                self.is_found = True            
        else:  
            filepath = os.path.join(f"C:/Program Files/Pixologic")            
            #TODO: add maxon path detection here
            #filepath = os.path.join(f"C:/Program Files/Maxon")
            #find non version paths
            if os.path.isdir(filepath):
                i,zfolder = utils.max_list_value(os.listdir(filepath))
                utils.prefs().zbrush_exec = os.path.join(filepath, zfolder, 'ZBrush.exe')
                ui.ShowReport(self, [utils.prefs().zbrush_exec], "GoB: Zbrush default installation found", 'COLORSET_03_VEC')
                self.is_found = True  

    if not self.is_found:
        print('GoB: Zbrush executable not found')

    return self.is_found



def is_file_empty(file_path):
    """ Check if file is empty by confirming if its size is 0 bytes"""
    return os.path.exists(file_path) and os.stat(file_path).st_size == 0



class GoB_OT_GoZ_Installer(Operator):
    ''' Run the Pixologic GoZ installer 
        /Troubleshoot Help/GoZ_for_ZBrush_Installer'''
    bl_idname = "gob.install_goz" 
    bl_label = "Run GoZ Installer"

    def execute(self, context):
        """Install GoZ for Windows""" 
        path_exists = find_zbrush(self, context, isMacOS)
        if path_exists:
            if isMacOS:
                path = utils.prefs().zbrush_exec.strip("ZBrush.app")  
                GOZ_INSTALLER = os.path.join(f"{path}Troubleshoot Help/GoZ_for_ZBrush_Installer_OSX.app")
                Popen(['open', '-a', GOZ_INSTALLER])  
            else: 
                path = utils.prefs().zbrush_exec.strip("ZBrush.exe")           
                GOZ_INSTALLER = os.path.join(f"{path}Troubleshoot Help/GoZ_for_ZBrush_Installer_WIN.exe")
                Popen([GOZ_INSTALLER], shell=True)
        else:
            bpy.ops.gob.search_zbrush('INVOKE_DEFAULT')
        return {'FINISHED'}