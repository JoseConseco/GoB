import bpy
import numpy
import addon_utils
import requests
from bpy.types import Operator 

def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 


update_available = None  
class AU_OT_SearchUpdates(Operator):
    ''' Look for a new Addon version on Github '''
    bl_idname = "au.check_updates"
    bl_label = "Check for Updates" 
    
    button_input: bpy.props.IntProperty()

    def max_tag(self, list):
        i = numpy.argmax(list)
        v = list[i]
        return (i, v)

    def find_new_version(self, api_path): 
        #EXPERIMENTAL VERSIONS
        if prefs().experimental_versions:
            response  = requests.get(api_path + "/tags")           # https://api.github.com/repos/JoseConseco/GoB/tags
            gitrelease = response.json()
            #print("gitrelease", gitrelease)
            tags = []
            for tag in gitrelease:
                version = tag.get('name')    # "name": "v3_5_1",
                tags.append(version)
            i, version = self.max_tag(tags)

            return version
        else:            
            print("experimental_versions: ", prefs().experimental_versions) 
            print("path: ", api_path + "/releases/latest")
            response  = requests.get(api_path + "/releases/latest")           # https://api.github.com/repos/JoseConseco/GoB/releases/latest
            gitrelease = response.json()
            version = gitrelease.get('tag_name')    # "tag_name": "v3_5_1",
            
            return version


    def download_new_version(self, api_path, new_version, zip_file, zip_file_url): 
        #import zipfile        
        # open release page 
        import webbrowser
        
        #EXPERIMENTAL VERSIONS
        if prefs().experimental_versions:        
            release_page = api_path + "/zipball/" + new_version  # "zipball_url": "https://api.github.com/repos/JoseConseco/GoB/zipball/v3_5_1",
        else:
            release_page = prefs().repository_path + "/releases"   # "https://github.com/JoseConseco/GoB/releases") 

        webbrowser.open_new_tab(release_page)


        #response  = requests.get(api_path)
        #gitrelease = response.json()        
        #zip_file_url = gitrelease.get('zipball_url')     # "zipball_url": "https://api.github.com/repos/JoseConseco/GoB/zipball/v3_5_1",
        #zip_file_url ='https://github.com/JoseConseco/GoB/archive/v3_5_1.zip'
        #print("zip_file_url", zip_file_url)

        #download = requests.get(zip_file_url)
        """ with open(zip_file, 'wb') as f:
            print("downloading update", zip_file)
            f.write(download.content)    """


    def addon_version(self):
        for mod in addon_utils.modules():
            if mod.bl_info.get('name') == 'GoB':
                n = self.extract_numbers(str(mod.bl_info.get('version', (-1, -1, -1))))
                version = "v"+ str(n[0]) + "_"+ str(n[1]) + "_"+ str(n[2])
                return version


    def extract_numbers(self, input_str):    
        if input_str is None or input_str == '':
            return 0
        number = [n for n in input_str if n.isdigit()] 
        return number


    def execute(self, context): 
        global update_available         
        api_path = prefs().repository_path.replace("https://github.com/", "https://api.github.com/repos/")

        print("self.button_input: ", self.button_input)
        if self.button_input != -1:
            try:    
                response  = requests.get(api_path + "/releases/latest")   
                if response.status_code == 200:         
                    print("self.button_input1: ", self.button_input)
                    current_version = self.addon_version()
                    new_version = self.find_new_version(api_path)
                    print("\n\nCurrent: ", current_version, "\nRelease: ", new_version)  

                    if new_version > current_version:
                        print("Addon update available: ", new_version)                     
                        if update_available and self.button_input == 1:
                            temp_path = context.preferences.filepaths.temporary_directory 
                            zip_file  = (temp_path + prefs().zip_filename)
                            #print("temp_path ", temp_path, zip_file)               
                            zip_file_url = prefs().repository_path + "/archive/" + new_version + ".zip" #'https://github.com/JoseConseco/GoB/archive/v3_5_1.zip'
                            self.download_new_version(api_path, new_version, zip_file, zip_file_url)                    
                        update_available = new_version
                    else:
                        print("Addon is up to date: ", current_version)
                        update_available = False  
                
                if response.status_code == 403:   #"message":"API rate limit exceeded for IP
                    update_available = 'TIME'

            except requests.ConnectionError as e:
                print("update doesn't exists!", e)              
                update_available = False


        
        #bpy.ops.preferences.addon_install(overwrite=True, target='DEFAULT', filepath=package, filter_folder=True, filter_python=True, filter_glob='*.py;*.zip')
        '''
        Install an add-on
        Parameters
        overwrite (boolean, (optional)) – Overwrite, Remove existing add-ons with the same ID
        target (enum in ['DEFAULT', 'PREFS'], (optional)) – Target Path
        filepath (string, (optional, never None)) – filepath
        filter_folder (boolean, (optional)) – Filter folders
        filter_python (boolean, (optional)) – Filter python
        filter_glob (string, (optional, never None)) – filter_glob
        '''

        return {'FINISHED'}
    
    
""" class BAU_OT_UpdateAddon(Operator):
    ''' update addon '''
    bl_idname = "au.update_addon"
    bl_label = "update_addon"  
    
    def download_new_version_version(self, url, save_path, download_path):  
            import webbrowser
            import requests, zipfile, io

            response  = requests.get(url)
            gitrelease = response.json()        
            #zip_file_url = gitrelease.get('zipball_url')     # "zipball_url": "https://api.github.com/repos/JoseConseco/GoB/zipball/v3_5_1",
            #print("zip_file_url", zip_file_url)
            #download_path ='https://github.com/JoseConseco/GoB/archive/v3_5_1.zip'
            webbrowser.open_new_tab(download_path)

            #download = requests.get(download_path)
            ''' with open(save_path, 'wb') as f:
                print("downloading update", save_path)
                f.write(download.content)   '''
    
    def execute(self, context):
        package = "c:/temp/!myaddon.zip"                    
        download_path = 'https://github.com/JoseConseco/GoB/archive/' + new_version + '.zip'

"""
