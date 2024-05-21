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

from . import utils, reports

def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 

def gob_init_os_paths():   
    isMacOS = False
    useZSH = False
    import platform
    if platform.system() == 'Windows':  
        print("GoB Found System: ", platform.system())
        isMacOS = False
        PATH_GOZ_PIXOLOGIC = os.path.join(os.environ['PUBLIC'] , "Pixologic")
        PATH_GOZ_MAXON = os.path.join(os.environ['PUBLIC'] , "Maxon")

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
        PATH_GOZ_PIXOLOGIC = os.path.join("/Users/Shared/Pixologic")
        PATH_GOZ_MAXON = os.path.join("/Users/Shared/Maxon")
    else:
        print("GoB Unkonwn System: ", platform.system())
        PATH_GOZ_PIXOLOGIC = False ## NOTE: GOZ seems to be missing, reinstall from zbrush
        PATH_GOZ_MAXON = False ## NOTE: GOZ seems to be missing, reinstall from zbrush
    
    PATH_GOB =  os.path.abspath(os.path.dirname(__file__))
    PATH_BLENDER = os.path.join(bpy.app.binary_path)
    
    return isMacOS, PATH_GOB, PATH_BLENDER, PATH_GOZ_PIXOLOGIC, PATH_GOZ_MAXON


def find_zbrush(self, context, isMacOS):
    #get the highest version of zbrush and use it as default zbrush to send to
    self.is_found = False 
    if prefs().zbrush_exec:        
        #OSX .app files are considered packages and cant be recognized with path.isfile and needs a special condition
        if isMacOS:
            if os.path.isdir(prefs().zbrush_exec) and 'zbrush.app' in str.lower(prefs().zbrush_exec):
                self.is_found = True   

        else: #is PC
            if os.path.isfile(prefs().zbrush_exec):  #validate if working file here    
                #check if path contains zbrush, that should identify a zbrush executable
                if 'zbrush.exe' in str.lower(prefs().zbrush_exec): 
                    self.is_found = True

            elif os.path.isdir(prefs().zbrush_exec): #search for zbrush files in this folder and its subfolders 
                for folder in os.listdir(prefs().zbrush_exec): 
                    if "zbrush" in str.lower(folder):     #search for content inside folder that contains zbrush
                        #search subfolders for executables
                        if os.path.isdir(os.path.join(prefs().zbrush_exec, folder)): 
                            i,zfolder = utils.max_list_value(os.listdir(os.path.join(prefs().zbrush_exec)))
                            for file in os.listdir(os.path.join(prefs().zbrush_exec, zfolder)):
                                if ('zbrush.exe' in str.lower(file) in str.lower(file)):            
                                    prefs().zbrush_exec = os.path.join(prefs().zbrush_exec, zfolder, file)           
                                    self.is_found = True   

                        #find executable
                        if os.path.isfile(os.path.join(prefs().zbrush_exec,folder)) and ('zbrush.exe' in str.lower(folder) in str.lower(folder)):            
                            prefs().zbrush_exec = os.path.join(prefs().zbrush_exec, folder)           
                            self.is_found = True  

    else:    # the  applications default path can try if zbrush is installed in its defaut location  
        #look for zbrush in default installation path 
        if isMacOS:
            folder_List = []                 
            filepath = os.path.join(f"/Applications")
            if os.path.isdir(filepath):
                [folder_List.append(i) for i in os.listdir(filepath) if 'zbrush' in str.lower(i)]
                i, zfolder = utils.max_list_value(folder_List)
                prefs().zbrush_exec = os.path.join(filepath, zfolder, 'ZBrush.app')
                reports.ShowReport(self, [prefs().zbrush_exec], "GoB: Zbrush default installation found", 'COLORSET_03_VEC') 
                self.is_found = True            
        else:  
            filepath = os.path.join(f"C:/Program Files/Pixologic")
            #find non version paths
            if os.path.isdir(filepath):
                i,zfolder = utils.max_list_value(os.listdir(filepath))
                prefs().zbrush_exec = os.path.join(filepath, zfolder, 'ZBrush.exe')
                reports.ShowReport(self, [prefs().zbrush_exec], "GoB: Zbrush default installation found", 'COLORSET_03_VEC')
                self.is_found = True  

    if not self.is_found:
        print('GoB: Zbrush executable not found')

    return self.is_found