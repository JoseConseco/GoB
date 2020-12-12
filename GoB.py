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
import shutil
from subprocess import Popen
import addon_utils
import bmesh
import mathutils
import math
import time
from struct import pack, unpack
import string
import numpy
from bpy_extras.io_utils import ImportHelper 
from bpy.types import Operator 


def gob_init_os_paths():   
    isMacOS = False
    import platform
    if platform.system() == 'Windows':  
        print("GoB Found System: ", platform.system())
        isMacOS = False
        #if os.path.isfile(os.environ['PUBLIC'] + "/Pixologic/GoZBrush/GoZBrushFromApp.exe"):
        PATH_GOZ = (os.environ['PUBLIC'] + "/Pixologic").replace("\\", "/")
    elif platform.system() == 'Darwin': #osx
        print("GoB Found System: ", platform.system())
        isMacOS = True
        #print(os.path.isfile("/Users/Shared/Pixologic/GoZBrush/GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"))
        PATH_GOZ = "/Users/Shared/Pixologic"
    else:
        print("GoB Unkonwn System: ", platform.system())
        PATH_GOZ = False ## NOTE: GOZ seems to be missing, reinstall from zbrush
    
    PATH_GOB =  os.path.abspath(os.path.dirname(__file__))
    PATH_BLENDER = bpy.app.binary_path.replace("\\", "/")

    return isMacOS, PATH_GOZ, PATH_GOB, PATH_BLENDER


isMacOS, PATH_GOZ, PATH_GOB, PATH_BLENDER = gob_init_os_paths()


time_interval = 2.0  # Check GoZ import for changes every 2.0 seconds
run_background_update = False
icons = None
cached_last_edition_time = time.time() - 10.0

preview_collections = {}
def draw_goz_buttons(self, context):
    global run_background_update, icons
    icons = preview_collections["main"]
    pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    if context.region.alignment != 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)

        if pref.show_button_text:
            row.operator(operator="scene.gob_export", text="Export", emboss=True, icon_value=icons["GOZ_SEND"].icon_id)
            if run_background_update:
                row.operator(operator="scene.gob_import", text="Import", emboss=True, depress=True, icon_value=icons["GOZ_SYNC_ENABLED"].icon_id)
            else:
                row.operator(operator="scene.gob_import", text="Import", emboss=True, depress=False, icon_value=icons["GOZ_SYNC_DISABLED"].icon_id)
        else:
            row.operator(operator="scene.gob_export", text="", emboss=True, icon_value=icons["GOZ_SEND"].icon_id)
            if run_background_update:
                row.operator(operator="scene.gob_import", text="", emboss=True, depress=True, icon_value=icons["GOZ_SYNC_ENABLED"].icon_id)
            else:
                row.operator(operator="scene.gob_import", text="", emboss=True, depress=False, icon_value=icons["GOZ_SYNC_DISABLED"].icon_id)

start_time = None
class GoB_OT_import(Operator):
    bl_idname = "scene.gob_import"
    bl_label = "GOZ import"
    bl_description = "GoZ Import. Activate to enable Import from GoZ"
    
    
    def GoZit(self, pathFile):     
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences   

        if pref.performance_profiling: 
            print("\n", 100*"=")
            start_time = profiler(time.time(), "Start Import Profiling")
            start_total_time = profiler(time.time(), "")

        utag = 0
        vertsData = []
        facesData = []
        objMat = None
        diff, disp, norm =  None, None, None
        exists = os.path.isfile(pathFile)
        if not exists:
            print(f'Cant read mesh from: {pathFile}. Skipping')
            return
        
        with open(pathFile, 'rb') as goz_file:
            goz_file.seek(36, 0)
            lenObjName = unpack('<I', goz_file.read(4))[0] - 16
            goz_file.seek(8, 1)
            obj_name = unpack('%ss' % lenObjName, goz_file.read(lenObjName))[0]
            # remove non ascii chars eg. /x 00
            objName = ''.join([letter for letter in obj_name[8:].decode('utf-8') if letter in string.printable])
            print(f"Importing: {pathFile, objName}")            
            tag = goz_file.read(4)
            
            while tag:                
                # Name
                if tag == b'\x89\x13\x00\x00':
                    print("name:", tag)
                    cnt = unpack('<L', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)

                # Vertices
                elif tag == b'\x11\x27\x00\x00':  
                    #print("Vertices:", tag)                    
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        co1 = unpack('<f', goz_file.read(4))[0]
                        co2 = unpack('<f', goz_file.read(4))[0]
                        co3 = unpack('<f', goz_file.read(4))[0]
                        vertsData.append((co1, co2, co3))
                
                # Faces
                elif tag == b'\x21\x4e\x00\x00':  
                    #print("Faces:", tag)
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        v1 = unpack('<L', goz_file.read(4))[0]
                        v2 = unpack('<L', goz_file.read(4))[0]
                        v3 = unpack('<L', goz_file.read(4))[0]
                        v4 = unpack('<L', goz_file.read(4))[0]
                        if v4 == 0xffffffff:
                            facesData.append((v1, v2, v3))
                        elif v4 == 0:
                            facesData.append((v4, v1, v2, v3))
                        else:
                            facesData.append((v1, v2, v3, v4))
                # UVs
                elif tag == b'\xa9\x61\x00\x00':  
                    #print("UVs:", tag)
                    break
                # Polypainting
                elif tag == b'\xb9\x88\x00\x00':  
                    #print("Polypainting:", tag)
                    break
                # Mask
                elif tag == b'\x32\x75\x00\x00':  
                    #print("Mask:", tag)
                    break
                # Polyroups
                elif tag == b'\x41\x9c\x00\x00': 
                    #print("Polyroups:", tag) 
                    break
                # End
                elif tag == b'\x00\x00\x00\x00':  
                    #print("End:", tag)
                    break
                # Unknown tags
                else:
                    print("Unknown tag:{0}".format(tag))
                    if utag >= 10:
                        print("...Too many mesh tags unknown...\n")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                tag = goz_file.read(4)
                
            if pref.performance_profiling:  
                start_time = profiler(start_time, "Unpack Mesh Data")

            # create new object
            if not objName in bpy.data.objects.keys():
                me = bpy.data.meshes.new(objName)  
                obj = bpy.data.objects.new(objName, me)
                bpy.context.view_layer.active_layer_collection.collection.objects.link(obj) 
                me.from_pydata(vertsData, [], facesData)     
                #me.transform(obj.matrix_world.inverted())      
           
            # object already exist
            else:                
                obj = bpy.data.objects[objName]                
                me = obj.data
                #mesh has same vertex count
                if len(me.vertices) == len(vertsData): 
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    bm.faces.ensure_lookup_table() 
                    #udpate vertex positions
                    for i, v in enumerate(bm.verts):
                        v.co  = mathutils.Vector(vertsData[i])  
                    bm.to_mesh(me)   
                    bm.free()

                #mesh has different vertex count
                else:              
                    me.clear_geometry() #NOTE: if this is done in edit mode we get a crash                         
                    me.from_pydata(vertsData, [], facesData)
                    #obj.data = me
           
            me,_ = apply_transformation(me, is_import=True)
            # assume we have to reverse transformation from obj mode, this is needed after matrix transfomrmations      
            me.transform(obj.matrix_world.inverted())         
           
            # update mesh data after transformations to fix normals 
            me.validate(verbose=True)
            me.update(calc_edges=True, calc_edges_loose=True) 

            # make object active
            obj.select_set(True) 
            bpy.context.view_layer.objects.active = obj

            vertsData.clear()
            facesData.clear()

            if pref.performance_profiling:  
                start_time = profiler(start_time, "Make Mesh")
                
            
            utag = 0
            while tag:
                
                # UVs
                if tag == b'\xa9\x61\x00\x00':                    
                    print("Import UV: ", pref.import_uv)

                    if pref.import_uv:  
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]     # face count
                        bm = bmesh.new()
                        bm.from_mesh(me)
                        bm.faces.ensure_lookup_table()
                        if me.uv_layers:
                            if pref.import_uv_name in me.uv_layers:                            
                                uv_layer = bm.loops.layers.uv.get(pref.import_uv_name)
                            else:
                                uv_layer = bm.loops.layers.uv.new(pref.import_uv_name)
                        else:
                            uv_layer = bm.loops.layers.uv.new(pref.import_uv_name) 
                        uv_layer = bm.loops.layers.uv.verify()

                        for face in bm.faces:
                            for index, loop in enumerate(face.loops):            
                                x, y = unpack('<2f', goz_file.read(8)) 
                                loop[uv_layer].uv = x, 1.0-y
                            #uv's always have 4 coords so its required to read one more if a trinalge is in the mesh
                            # zbrush seems to always write out 4 coords            
                            if index < 3:       
                                x, y = unpack('<2f', goz_file.read(8))

                        bm.to_mesh(me)   
                        bm.free()                       
                        me.update(calc_edges=True, calc_edges_loose=True)  
                        if pref.performance_profiling: 
                            start_time = profiler(start_time, "UV Map") 
                    else:
                        utag += 1
                        cnt = unpack('<I', goz_file.read(4))[0] - 8
                        goz_file.seek(cnt, 1)
                        

                # Polypainting
                elif tag == b'\xb9\x88\x00\x00': 
                    print("Import Polypaint: ", pref.import_polypaint)  

                    if pref.import_polypaint:
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]  
                        polypaintData = []
                        for i in range(cnt): 
                            colordata = unpack('<3B', goz_file.read(3)) # Color
                            unpack('<B', goz_file.read(1))  # Alpha
                            alpha = 1                        

                            #convert color to vector                         
                            rgb = [x / 255.0 for x in colordata]    
                            rgb.reverse()                    
                            rgba = rgb + [alpha]                                          
                            polypaintData.append(tuple(rgba))                      
                        
                        if pref.performance_profiling: 
                            start_time = profiler(start_time, "Polypaint Unpack")

                        if colordata:                   
                            bm = bmesh.new()
                            bm.from_mesh(me)
                            bm.faces.ensure_lookup_table()
                            if me.vertex_colors:                            
                                if pref.import_polypaint_name in me.vertex_colors: 
                                    color_layer = bm.loops.layers.color.get(pref.import_polypaint_name)
                                else:
                                    color_layer = bm.loops.layers.color.new(pref.import_polypaint_name)                                    
                            else:
                                color_layer = bm.loops.layers.color.new(pref.import_polypaint_name)                
                            
                            for face in bm.faces:
                                for loop in face.loops:
                                    loop[color_layer] = polypaintData[loop.vert.index]

                            bm.to_mesh(me)                        
                            me.update(calc_edges=True, calc_edges_loose=True)  
                            bm.free()
                            
                        polypaintData.clear()    
                        if pref.performance_profiling: 
                            start_time = profiler(start_time, "Polypaint Assign")
                    else:
                        utag += 1
                        cnt = unpack('<I', goz_file.read(4))[0] - 8
                        goz_file.seek(cnt, 1)

                # Mask
                elif tag == b'\x32\x75\x00\x00':   
                    print("Import Mask: ", pref.import_mask)
                    
                    
                    if pref.import_mask:
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]

                        if 'mask' in obj.vertex_groups:
                            obj.vertex_groups.remove(obj.vertex_groups['mask'])
                        groupMask = obj.vertex_groups.new(name='mask')

                        for faceIndex in range(cnt):
                            weight = unpack('<H', goz_file.read(2))[0] / 65535                          
                            groupMask.add([faceIndex], 1.-weight, 'ADD')  

                        if pref.performance_profiling: 
                            start_time = profiler(start_time, "Mask")
                    else:
                        utag += 1
                        cnt = unpack('<I', goz_file.read(4))[0] - 8
                        goz_file.seek(cnt, 1)

                # Polyroups
                elif tag == b'\x41\x9c\x00\x00':   
                    print("Import Polyroups: ", pref.import_polygroups_to_vertexgroups, pref.import_polygroups_to_facemaps)
                    
                    #wipe face maps before importing new ones due to random naming
                    if pref.import_polygroups_to_facemaps:
                        for i,facemap in enumerate(obj.face_maps):                              
                            obj.face_maps.remove(facemap)


                    groupsData = []
                    facemapsData = []
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]     # get polygroup faces
                    #print("polygroup data:", cnt)
                    
                    for i in range(cnt):    # faces of each polygroup
                        group = unpack('<H', goz_file.read(2))[0]
                        #print("polygroup data:", i, group, hex(group))

                        # vertex groups import
                        if pref.import_polygroups_to_vertexgroups:
                            if group not in groupsData: #this only works if mask is already there
                                if str(group) in obj.vertex_groups:
                                    obj.vertex_groups.remove(obj.vertex_groups[str(group)])
                                vg = obj.vertex_groups.new(name=str(group))
                                groupsData.append(group)
                            else:
                                vg = obj.vertex_groups[str(group)]
                            vg.add(list(me.polygons[i].vertices), 1.0, 'ADD')    # add vertices to vertex group
                        
                        # Face maps import
                        if pref.import_polygroups_to_facemaps:
                            if group not in facemapsData:
                                if str(group) in obj.face_maps:
                                    obj.face_maps.remove(obj.face_maps[str(group)])
                                faceMap = obj.face_maps.new(name=str(group))
                                facemapsData.append(group)
                            else:                        
                                faceMap = obj.face_maps[str(group)] 

                            try:
                                if obj.data.polygons[i]:
                                    faceMap.add([i])     # add faces to facemap
                            except:
                                pass
                            
                    try:
                        print("VGs: ", obj.vertex_groups.get('0'))
                        obj.vertex_groups.remove(obj.vertex_groups.get('0'))
                    except:
                        pass

                    try:
                        print("FMs: ", obj.face_maps.get('0'))
                        obj.face_maps.remove(obj.face_maps.get('0'))
                    except:
                        pass
                    
                    groupsData.clear()
                    facemapsData.clear()

                    if pref.performance_profiling: 
                        start_time = profiler(start_time, "Polyroups")

                # End
                elif tag == b'\x00\x00\x00\x00': 
                    break
                
                # Diffuse Texture 
                elif tag == b'\xc9\xaf\x00\x00':  
                    #print("Diff map:", tag)
                    texture_name = (obj.name + pref.import_diffuse_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    diffName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(diffName.decode('utf-8'))
                    img = bpy.data.images.load(diffName.strip().decode('utf-8'), check_existing=True) 
                    img.name = texture_name                                        
                    img.reload()
                    
                    if not texture_name in bpy.data.textures:
                        txtDiff = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDiff.image = img            
                    diff = img
                

                # Displacement Texture 
                elif tag == b'\xd9\xd6\x00\x00':  
                    #print("Disp map:", tag)
                    texture_name = (obj.name + pref.import_displace_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    dispName = unpack('%ss' % cnt, goz_file.read(cnt))[0]                    
                    print(dispName.decode('utf-8'))                    
                    img = bpy.data.images.load(dispName.strip().decode('utf-8'), check_existing=True)  
                    img.name = texture_name                                       
                    img.reload()

                    if not texture_name in bpy.data.textures:
                        txtDisp = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDisp.image = img
                    disp = img

                # Normal Map Texture
                elif tag == b'\x51\xc3\x00\x00':   
                    #print("Normal map:", tag)
                    texture_name = (obj.name + pref.import_normal_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    normName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(normName.decode('utf-8'))
                    img = bpy.data.images.load(normName.strip().decode('utf-8'), check_existing=True) 
                    img.name = texture_name                                       
                    img.reload()
                    
                    if not texture_name in bpy.data.textures:
                        txtNorm = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtNorm.image = img
                    norm = img
                
                # Unknown tags
                else: 
                    print("Unknown tag:{0}".format(tag))
                    if utag >= 10:
                        print("...Too many object tags unknown...\n")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)

                tag = goz_file.read(4)
                
            if pref.performance_profiling:                
                start_time = profiler(start_time, "Textures")
            
            # Materials
            if pref.import_material == 'NONE':
                print("Import Material: ", pref.import_material) 
            else:
                
                if len(obj.material_slots) > 0:
                    #print("material slot: ", obj.material_slots[0])
                    if obj.material_slots[0].material is not None:
                        objMat = obj.material_slots[0].material
                    else:
                        objMat = bpy.data.materials.new(objName)
                        obj.material_slots[0].material = objMat
                else:
                    objMat = bpy.data.materials.new(objName)
                    obj.data.materials.append(objMat)

                if pref.import_material == 'POLYPAINT':                    
                    if pref.import_polypaint_name in me.vertex_colors:
                        create_node(objMat, pref, diff, norm, disp)  
                    
                elif pref.import_material == 'TEXTURES':
                    create_node(objMat, pref, diff, norm, disp)  
                    
                elif pref.import_material == 'POLYGROUPS':
                    create_node(objMat, pref, diff, norm, disp)  
          
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Material Node")
                

            # #apply face maps to sculpt mode face sets
            if pref.apply_facemaps_to_facesets and  bpy.app.version > (2, 82, 7):                
                bpy.ops.object.mode_set(bpy.context.copy(), mode='SCULPT')                 
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            override = {'window': window, 'screen': screen, 'area': area}
                            bpy.ops.sculpt.face_sets_init(override, mode='FACE_MAPS')   
                            break                   
                if pref.performance_profiling:                
                    start_time = profiler(start_time, "Init Face Sets")

                # reveal all mesh elements (after the override for the face maps the elements without faces are hidden)                                 
                bpy.ops.object.mode_set(bpy.context.copy(), mode='EDIT') 
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            override = {'window': window, 'screen': screen, 'area': area}
                            bpy.ops.mesh.reveal(override)
                            break  

                if pref.performance_profiling:                
                    start_time = profiler(start_time, "Reveal Mesh Elements")
                                           
            if pref.performance_profiling: 
                profiler(start_total_time, "Total Import Time")  
                print(30*"=")
        return
             

    def execute(self, context):
        goz_obj_paths = []
        try:
            with open(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt", 'rt') as goz_objs_list:
                for line in goz_objs_list:
                    goz_obj_paths.append(line.strip() + '.GoZ')

        except PermissionError:
            print("File already in use! Try again Later")

        if len(goz_obj_paths) == 0:
            self.report({'INFO'}, message="No goz files in GoZ_ObjectList.txt")
            return{'CANCELLED'}

        currentContext = 'OBJECT'
        if context.object and context.object.mode != 'OBJECT':
            currentContext = context.object.mode
            print("currentContext: ", currentContext)
            # ! cant get proper context from timers for now to change mode: https://developer.blender.org/T62074
            bpy.ops.object.mode_set(context.copy(), mode='OBJECT') #hack
        
        for ztool_path in goz_obj_paths:
            self.GoZit(ztool_path)
            bpy.ops.object.mode_set(context.copy(), mode=currentContext)
        self.report({'INFO'}, "Done")
        return{'FINISHED'}

    
    def invoke(self, context, event):        
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
        if pref.import_method == 'AUTOMATIC':
            global run_background_update
            if run_background_update:
                if bpy.app.timers.is_registered(run_import_periodically):
                    bpy.app.timers.unregister(run_import_periodically)
                    print('Disabling GOZ background listener')
                run_background_update = False
            else:
                if not bpy.app.timers.is_registered(run_import_periodically):
                    bpy.app.timers.register(run_import_periodically, persistent=True)
                    print('Enabling GOZ background listener')
                run_background_update = True
            return{'FINISHED'}
        else:
            if run_background_update:
                if bpy.app.timers.is_registered(run_import_periodically):
                    bpy.app.timers.unregister(run_import_periodically)
                    print('Disabling GOZ background listener')
                run_background_update = False
            return{'FINISHED'}


def create_node(mat, pref, diff=None, norm=None, disp=None):

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    """ for node in nodes:
        print(node) """
    shader_node = nodes.get('Principled BSDF')  
    output_node = nodes.get('Material Output')    
    
    if pref.import_material == 'TEXTURES':        
        # Diffiuse Color Map
        if diff:
            diffTxt_node = False  
            for node in nodes:
                if node.bl_idname == 'ShaderNodeTexImage' and node.image.name == diff.name:
                    diffTxt_node = node
            if not diffTxt_node:    
                diffTxt_node = nodes.new('ShaderNodeTexImage')
                diffTxt_node.location = -700, 500  
                diffTxt_node.image = diff
                diffTxt_node.label = 'Diffuse Color Map'
                diffTxt_node.image.colorspace_settings.name = pref.import_diffuse_colorspace
                mat.node_tree.links.new(shader_node.inputs[0], diffTxt_node.outputs[0])

        # Normal Map
        if norm:
            norm_node = False  
            normTxt_node = False 
            for node in nodes:
                if node.bl_idname == 'ShaderNodeTexImage' and node.image.name == norm.name:
                    normTxt_node = node
                if node.bl_idname == 'ShaderNodeNormalMap':
                    norm_node = node
            if not norm_node:
                norm_node = nodes.new('ShaderNodeNormalMap')
                norm_node.location = -300, -100  
                mat.node_tree.links.new(shader_node.inputs[19], norm_node.outputs[0])
            if not normTxt_node:    
                normTxt_node = nodes.new('ShaderNodeTexImage')
                normTxt_node.location = -700, -100  
                normTxt_node.image = norm
                normTxt_node.label = 'Normal Map'
                normTxt_node.image.colorspace_settings.name = pref.import_normal_colorspace
                mat.node_tree.links.new(norm_node.inputs[1], normTxt_node.outputs[0])

        # Displacement Map
        if disp:
            disp_node = False  
            dispTxt_node = False  
            for node in nodes:
                if node.bl_idname == 'ShaderNodeTexImage' and node.image.name == disp.name:
                    dispTxt_node = node     
                if node.bl_idname == 'ShaderNodeDisplacement':
                    disp_node = node
            if not disp_node:
                disp_node = nodes.new('ShaderNodeDisplacement')
                disp_node.location = -300, 200  
                mat.node_tree.links.new(output_node.inputs[2], disp_node.outputs[0])
            if not dispTxt_node:    
                dispTxt_node = nodes.new('ShaderNodeTexImage')
                dispTxt_node.location = -700, 200  
                dispTxt_node.image = disp
                dispTxt_node.label = 'Displacement Map'
                dispTxt_node.image.colorspace_settings.name = pref.import_displace_colorspace
                mat.node_tree.links.new(disp_node.inputs[3], dispTxt_node.outputs[0])

    if pref.import_material == 'POLYPAINT':
        vcol_node = False   
        for node in nodes:
            if node.bl_idname == 'ShaderNodeVertexColor':
                if pref.import_polypaint_name in node.layer_name:
                    vcol_node = nodes.get(node.name) 
        if not vcol_node:
            vcol_node = nodes.new('ShaderNodeVertexColor')
            vcol_node.location = -300, 200
            vcol_node.layer_name = pref.import_polypaint_name    
            mat.node_tree.links.new(shader_node.inputs[0], vcol_node.outputs[0])
    

def apply_transformation(me, is_import=True): 
    pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    mat_transform = None
    scale = 1.0
    
    if pref.use_scale == 'BUNITS':
        scale = bpy.context.scene.unit_settings.scale_length

    if pref.use_scale == 'MANUAL':        
        scale =  1/pref.manual_scale

    if pref.use_scale == 'ZUNITS':
        if bpy.context.active_object:
            obj = bpy.context.active_object
            i, max = max_list_value(obj.dimensions)
            scale =  1 / pref.zbrush_scale * max
            #print("unit scale 2: ", obj.dimensions, i, max, scale, obj.dimensions * scale)
            
    #import
    if pref.flip_up_axis:  # fixes bad mesh orientation for some people
        if pref.flip_forward_axis:
            if is_import:
                me.transform(mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]) * scale
                )
                me.flip_normals()
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]) * (1/scale)
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]) * scale
                )
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]) * (1/scale)
    else:
        if pref.flip_forward_axis:            
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]) * scale
                )
                me.flip_normals()
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]) * (1/scale)
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]) * scale
                )
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]) * (1/scale)
    return me, mat_transform
                
def profiler(start_time=0, string=None):               
    
    elapsed = time.time()
    print("{:.4f}".format(elapsed-start_time), "<< ", string)  
    start_time = time.time()
    return start_time  

def max_list_value(list):
    i = numpy.argmax(list)
    v = list[i]
    return (i, v)
    
def avg_list_value(list):
    avgData=[]
    for obj in list:
        i = numpy.argmax(obj)
        avgData.append(obj[i])
    avg = numpy.average(avgData)
    return (avg)


def run_import_periodically():
    # print("Runing timers update check")
    global cached_last_edition_time, run_background_update

    try:
        file_edition_time = os.path.getmtime(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt")
    except Exception as e:
        print(e)
        run_background_update = False
        if bpy.app.timers.is_registered(run_import_periodically):
            bpy.app.timers.unregister(run_import_periodically)
        return time_interval

    if file_edition_time > cached_last_edition_time:
        cached_last_edition_time = file_edition_time
        # ! cant get proper context from timers for now. Override context: https://developer.blender.org/T62074
        window = bpy.context.window_manager.windows[0]
        ctx = {'window': window, 'screen': window.screen, 'workspace': window.workspace}
        bpy.ops.scene.gob_import(ctx) #only call operator update is found (executing operatros is slow)
    else:
        # print("GOZ: Nothing to update")
        return time_interval
    
    if not run_background_update and bpy.app.timers.is_registered(run_import_periodically):
        bpy.app.timers.unregister(run_import_periodically)
    return time_interval


class GoB_OT_export(Operator):
    bl_idname = "scene.gob_export"
    bl_label = "Export to ZBrush"
    bl_description = "Export selected Objects to ZBrush"
    
    @classmethod
    def poll(cls, context):
        selected_objects = context.selected_objects
        if selected_objects:
            if selected_objects[0].visible_get and selected_objects[0].type == 'MESH':
                numFaces = len(selected_objects[0].data.polygons)
                if len(selected_objects) <= 1:
                    return numFaces
            #elif selected_objects[0].type == 'MESH':
            return selected_objects

    @staticmethod
    def apply_modifiers(obj, pref):
        dg = bpy.context.evaluated_depsgraph_get()
        if pref.export_modifiers == 'APPLY_EXPORT':
            # me = object_eval.to_mesh() #with modifiers - crash need to_mesh_clear()?
            me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            obj.data = me
            obj.modifiers.clear()
        elif pref.export_modifiers == 'ONLY_EXPORT':
            me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        else:
            me = obj.data

        #DO the triangulation of Ngons only, but do not write it to original object.    
        bm = bmesh.new()
        bm.from_mesh(me)
        #join traingles only that are result of ngon triangulation        
        for f in bm.faces:
            if len(f.edges) > 4:
                result = bmesh.ops.triangulate(bm, faces=[f])
                bmesh.ops.join_triangles(bm, faces= result['faces'], 
                                        cmp_seam=False, cmp_sharp=False, cmp_uvs=False, 
                                        cmp_vcols=False,cmp_materials=False, 
                                        angle_face_threshold=(math.pi), angle_shape_threshold=(math.pi))
        
        export_mesh = bpy.data.meshes.new(name=f'{obj.name}_goz')  # mesh is deleted in main loop anyway
        bm.to_mesh(export_mesh)
        bm.free()

        return export_mesh


    def exportGoZ(self, path, scn, obj, pathImport):
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences        
        PATH_PROJECT = pref.project_path.replace("\\", "/")   
        if pref.performance_profiling: 
            print("\n", 100*"=")
            start_time = profiler(time.time(), "Export Profiling: " + obj.name)
            start_total_time = profiler(time.time(), "-------------")
        
        # TODO: when linked system is finalized it could be possible to provide
        #  a option to modify the linked object. for now a copy
        #  of the linked object is created to goz it
        if obj.type == 'MESH':
            if obj.library:
                new_ob = obj.copy()
                new_ob.data = obj.data.copy()
                scn.collection.objects.link(new_ob)
                new_ob.select_set(state=True)
                obj.select_set(state=False)
                bpy.context.view_layer.objects.active = new_ob

                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Linked Object")
               
        me = self.apply_modifiers(obj, pref)
        me.calc_loop_triangles()
        me, mat_transform = apply_transformation(me, is_import=False)

        if pref.performance_profiling: 
            start_time = profiler(start_time, "Make Mesh")


        fileExt = '.bmp'
        
        # write GoB ZScript variables
        variablesFile = f"{PATH_GOZ}/GoZProjects/Default/GoB_variables.zvr"        
        with open(variablesFile, 'wb') as GoBVars:            
            GoBVars.write(pack('<4B', 0xE9, 0x03, 0x00, 0x00))
            #list size
            GoBVars.write(pack('<1B', 0x07))   #NOTE: n list items, update this when adding new items to list
            GoBVars.write(pack('<2B', 0x00, 0x00)) 

            # 0: fileExtension
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.GoZ')
            # 1: textureFormat   
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.bmp') 
            # 2: diffTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S            
            name = pref.import_diffuse_suffix
            GoBVars.write(name.encode('utf-8'))    
            # 3: normTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = pref.import_normal_suffix
            GoBVars.write(name.encode('utf-8'))   
            # 4: dispTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = pref.import_displace_suffix
            GoBVars.write(name.encode('utf-8')) 
            #5: GoB version   
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S         
            for mod in addon_utils.modules():
                if mod.bl_info.get('name') == 'GoB':
                    version = str(mod.bl_info.get('version', (-1, -1, -1)))
            GoBVars.write(version.encode('utf-8'))
            # 6: Project Path
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = pref.project_path
            GoBVars.write(name.encode('utf-8')) 

            #end  
            GoBVars.write(pack('<B', 0x00))  #. 
                 


        with open(pathImport + '/{0}.GoZ'.format(obj.name), 'wb') as goz_file:
            
            numFaces = len(me.polygons)
            numVertices = len(me.vertices)

            # --File Header--
            goz_file.write(b"GoZb 1.0 ZBrush GoZ Binary")
            goz_file.write(pack('<6B', 0x2E, 0x2E, 0x2E, 0x2E, 0x2E, 0x2E))
            goz_file.write(pack('<I', 1))  # obj tag
            goz_file.write(pack('<I', len(obj.name)+24))
            goz_file.write(pack('<Q', 1))
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write File Header")

            # --Object Name--
            goz_file.write(b'GoZMesh_' + obj.name.encode('utf-8'))
            goz_file.write(pack('<4B', 0x89, 0x13, 0x00, 0x00))
            goz_file.write(pack('<I', 20))
            goz_file.write(pack('<Q', 1))
            goz_file.write(pack('<I', 0))           
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Object Name")
            

            # --Vertices--
            goz_file.write(pack('<4B', 0x11, 0x27, 0x00, 0x00))
            goz_file.write(pack('<I', numVertices*3*4+16))
            goz_file.write(pack('<Q', numVertices))            
            for vert in me.vertices:
                modif_coo = obj.matrix_world @ vert.co      # @ is used for matrix multiplications
                modif_coo = mat_transform @ modif_coo
                goz_file.write(pack('<3f', modif_coo[0], modif_coo[1], modif_coo[2]))
                
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Vertices")
            

            # --Faces--
            goz_file.write(pack('<4B', 0x21, 0x4E, 0x00, 0x00))
            goz_file.write(pack('<I', numFaces*4*4+16))
            goz_file.write(pack('<Q', numFaces))
            for face in me.polygons:
                if len(face.vertices) == 4:
                    goz_file.write(pack('<4I', face.vertices[0],
                                face.vertices[1],
                                face.vertices[2],
                                face.vertices[3]))
                elif len(face.vertices) == 3:
                    goz_file.write(pack('<3I4B', face.vertices[0],
                                face.vertices[1],
                                face.vertices[2],
                                0xFF, 0xFF, 0xFF, 0xFF))

            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Faces")


            # --UVs--
            if me.uv_layers.active:
                uv_layer = me.uv_layers[0]
                goz_file.write(pack('<4B', 0xA9, 0x61, 0x00, 0x00))
                goz_file.write(pack('<I', len(me.polygons)*4*2*4+16))
                goz_file.write(pack('<Q', len(me.polygons)))
                for face in me.polygons:
                    for i, loop_index in enumerate(face.loop_indices):
                        goz_file.write(pack('<2f', uv_layer.data[loop_index].uv.x, 1. - uv_layer.data[loop_index].uv.y))
                    if i == 2:
                        goz_file.write(pack('<2f', 0., 1.))
                        
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write UV")


            # --Polypaint--
            if me.vertex_colors.active:
                vcoldata = me.vertex_colors.active.data # color[loop_id]
                vcolArray = bytearray([0] * numVertices * 3)
                #fill vcArray(vert_idx + rgb_offset) = color_xyz
                for loop in me.loops: #in the end we will fill verts with last vert_loop color
                    vert_idx = loop.vertex_index
                    vcolArray[vert_idx*3] = int(255*vcoldata[loop.index].color[0])
                    vcolArray[vert_idx*3+1] = int(255*vcoldata[loop.index].color[1])
                    vcolArray[vert_idx*3+2] = int(255*vcoldata[loop.index].color[2])

                goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                goz_file.write(pack('<I', numVertices*4+16))
                goz_file.write(pack('<Q', numVertices))

                for i in range(0, len(vcolArray), 3):
                    goz_file.write(pack('<B', vcolArray[i+2]))
                    goz_file.write(pack('<B', vcolArray[i+1]))
                    goz_file.write(pack('<B', vcolArray[i]))
                    goz_file.write(pack('<B', 0))
                vcolArray.clear()
            
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Polypaint")

            # --Mask--
            if not pref.export_clear_mask:
                for vertexGroup in obj.vertex_groups:
                    if vertexGroup.name.lower() == 'mask':
                        goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                        goz_file.write(pack('<I', numVertices*2+16))
                        goz_file.write(pack('<Q', numVertices))                        
                        for i in range(numVertices):                                
                            try:
                                goz_file.write(pack('<H', int((1.0 - vertexGroup.weight(i)) * 65535)))
                            except:
                                goz_file.write(pack('<H', 65535))                                
                
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Mask")
        
           
            # --Polygroups--     
            if not pref.export_polygroups == 'NONE':  
                print("Export Polygroups: ", pref.export_polygroups)
                import random

                #Polygroups from Face Maps
                if pref.export_polygroups == 'FACE_MAPS':
                    print(obj.face_maps.items)
                    if obj.face_maps.items:                   
                        goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                        goz_file.write(pack('<I', numFaces*2+16))
                        goz_file.write(pack('<Q', numFaces))  
                                                
                        groupColor=[]                        
                        #create a color for each facemap (0xffff)
                        for faceMap in obj.face_maps:
                            randcolor = "%5x" % random.randint(0x1111, 0xFFFF)
                            color = int(randcolor, 16)
                            groupColor.append(color)

                        if me.face_maps: 
                            for index, map in enumerate(me.face_maps[0].data):
                                if map.value >= 0:
                                    goz_file.write(pack('<H', groupColor[map.value]))  
                                else: #face without facemaps (value = -1)
                                    goz_file.write(pack('<H', 65535))
                        else:   #assign empty when no face maps are found                 
                            for face in me.polygons:         
                                goz_file.write(pack('<H', 65535))
                                 

                    if pref.performance_profiling: 
                        start_time = profiler(start_time, "Write FaceMaps") 
                

                # Polygroups from Vertex Groups
                if pref.export_polygroups == 'VERTEX_GROUPS':
                    goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                    goz_file.write(pack('<I', numFaces*2+16))
                    goz_file.write(pack('<Q', numFaces)) 


                    import random
                    groupColor=[]                        
                    #create a color for each facemap (0xffff)
                    for vg in obj.vertex_groups:
                        randcolor = "%5x" % random.randint(0x1111, 0xFFFF)
                        color = int(randcolor, 16)
                        groupColor.append(color)
                    #add a color for elements that are not part of a vertex group
                    groupColor.append(0)
                    

                    ''' 
                        # create a list of each vertex group assignement so one vertex can be in x amount of groups 
                        # then check for each face to which groups their vertices are MOST assigned to 
                        # and choose that group for the polygroup color if its on all vertices of the face
                    '''
                    vgData = []  
                    for face in me.polygons:
                        vgData.append([])
                        for vert in face.vertices:
                            for vg in me.vertices[vert].groups:
                                if vg.weight >= pref.export_weight_threshold and obj.vertex_groups[vg.group].name.lower() != 'mask':         
                                    vgData[face.index].append(vg.group)
                        
                        if vgData[face.index]:                            
                            group =  max(vgData[face.index], key = vgData[face.index].count)
                            count = vgData[face.index].count(group)
                            #print(vgData[face.index])
                            #print("face:", face.index, "verts:", len(face.vertices), "elements:", count, 
                            #"\ngroup:", group, "color:", groupColor[group] )                            
                            if len(face.vertices) == count:
                                #print("full:", face.index,  "\n")
                                goz_file.write(pack('<H', groupColor[group]))
                            else:
                                goz_file.write(pack('<H', 65535))
                        else:
                            goz_file.write(pack('<H', 65535))

                    #print(vgData)
                    #print(groupColor)

                    if pref.performance_profiling: 
                        start_time = profiler(start_time, "Write Polygroups")


                # Polygroups from materials
                if pref.export_polygroups == 'MATERIALS':
                    for index, slot in enumerate(obj.material_slots):
                        if not slot.material:
                            continue
                        verts = [v for f in obj.data.polygons
                                if f.material_index == index for v in f.vertices]
                        if len(verts):
                            vg = obj.vertex_groups.get(slot.material.name)
                            if vg is None:
                                vg = obj.vertex_groups.new(name=slot.material.name)
                                vg.add(verts, 1.0, 'ADD')
                else:
                    print("Export Polygroups: ", pref.export_polygroups)
                    

            # Diff, disp and norm maps
            diff = 0
            disp = 0
            norm = 0

            for mat in obj.material_slots:
                if mat.name:
                    material = bpy.data.materials[mat.name]
                    if material.use_nodes:
                        #print("material:", mat.name, "using nodes \n")
                        for node in material.node_tree.nodes:	
                            #print("node: ", node.type)                                
                            if node.type == 'TEX_IMAGE' and node.image:
                                #print("IMAGES: ", node.image.name, node.image)	
                                if (pref.import_diffuse_suffix) in node.image.name:                                
                                    diff = node.image
                                    print("diff", diff)
                                if (pref.import_displace_suffix) in node.image.name:
                                    disp = node.image
                                if (pref.import_normal_suffix) in node.image.name:
                                    norm = node.image
                            elif node.type == 'GROUP':
                                print("group found")
            
            scn.render.image_settings.file_format = 'BMP'
            #fileExt = ('.' + pref.texture_format.lower())
            fileExt = '.bmp'

            if diff:
                name = PATH_PROJECT + obj.name + pref.import_diffuse_suffix + fileExt
                try:
                    diff.save_render(name)
                    print(name)
                except:
                    pass
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xc9, 0xaf, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write diff")

            if disp:
                name = PATH_PROJECT + obj.name + pref.import_displace_suffix + fileExt
                try:
                    disp.save_render(name)
                    print(name)
                except:
                    pass
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xd9, 0xd6, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write disp")

            if norm:
                name = PATH_PROJECT + obj.name + pref.import_normal_suffix + fileExt                
                try:
                    norm.save_render(name)
                    print(name)
                except:
                    pass
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0x51, 0xc3, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write norm")

            # end
            goz_file.write(pack('16x'))
            
            if pref.performance_profiling: 
                profiler(start_time, "Write Textures")
                print(30*"-")
                profiler(start_total_time, "Total Export Time")
                print(30*"=")

        bpy.data.meshes.remove(me)
        return

    def execute(self, context):  

        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences             
        PATH_PROJECT = pref.project_path.replace("\\", "/") 
        #setup GoZ configuration
        #if not os.path.isfile(f"{PATH_GOZ}/GoZApps/Blender/GoZ_Info.txt"):  
        try:    #install in GoZApps if missing     
            source_GoZ_Info = f"{PATH_GOB}/Blender/"
            target_GoZ_Info = f"{PATH_GOZ}/GoZApps/Blender/"
            shutil.copytree(source_GoZ_Info, target_GoZ_Info, symlinks=True)            
        except FileExistsError: #if blender folder is found update the info file
            source_GoZ_Info = f"{PATH_GOB}/Blender/GoZ_Info.txt"
            target_GoZ_Info = f"{PATH_GOZ}/GoZApps/Blender/GoZ_Info.txt"
            shutil.copy2(source_GoZ_Info, target_GoZ_Info)  

            #write blender path to GoZ configuration
            #if not os.path.isfile(f"{PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt"): 
            with open(f"{PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt", 'wt') as GoZ_Config:
                GoZ_Config.write(f"PATH = \"{PATH_BLENDER}\"")
            #specify GoZ application
            with open(f"{PATH_GOZ}/GoZBrush/GoZ_Application.txt", 'wt') as GoZ_Application:
                GoZ_Application.write("Blender")            


        #update project path
        print("Project file path: ", f"{PATH_GOZ}/GoZBrush/GoZ_ProjectPath.txt")
        with open(f"{PATH_GOZ}/GoZBrush/GoZ_ProjectPath.txt", 'wt') as GoZ_Application:
            GoZ_Application.write(PATH_PROJECT)  
            

        # remove ZTL files since they mess up Zbrush importing subtools
        if pref.clean_project_path:
            for file_name in os.listdir(PATH_PROJECT):
                #print(file_name)
                if file_name.endswith(('GoZ', '.ztn', '.ZTL')):
                    print('cleaning file:', file_name)
                    os.remove(PATH_PROJECT + file_name)

        currentContext = 'OBJECT'
        if context.object and context.object.mode != 'OBJECT':            
            currentContext = context.object.mode
            bpy.ops.object.mode_set(bpy.context.copy(), mode='OBJECT')

        with open(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt", 'wt') as GoZ_ObjectList:
            for obj in context.selected_objects:
                if  obj.type == 'MESH':
                    numFaces = len(obj.data.polygons)
                    if numFaces:
                        self.escape_object_name(obj)
                        self.exportGoZ(PATH_GOZ, context.scene, obj, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj.name}\n')
                    else:
                        print("\n", obj.name, "has no faces and will not be exported. ZBrush can not import objects without faces")

                    
        global cached_last_edition_time
        cached_last_edition_time = os.path.getmtime(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt")
        PATH_ZBRUSH = pref.zbrush_exec
        PATH_SCRIPT = (f"{PATH_GOB}/ZScripts/GoB_Import.zsc").replace("\\", "/")
        
        if 'ZBrush.exe' in PATH_ZBRUSH:    
            Popen([PATH_ZBRUSH, PATH_SCRIPT])
        elif 'ZBrush.app' in PATH_ZBRUSH:
            Popen(['open', '-a', PATH_ZBRUSH, PATH_SCRIPT])     
        else:
            if isMacOS:
                filepath = f"/Applications/"
            else:
                filepath = f"C:/Program Files/Pixologic/"

            bpy.ops.gob.open_filebrowser('INVOKE_DEFAULT', filepath=filepath)
            #Popen([PATH_ZBRUSH, PATH_SCRIPT])
            
        if context.object:
            bpy.ops.object.mode_set(bpy.context.copy(), mode=currentContext)  
        return{'FINISHED'}


    def escape_object_name(self, obj):
        """
        Escape object name so it can be used as a valid file name.
        Keep only alphanumeric characters, underscore, dash and dot, and replace other characters with an underscore.
        Multiple consecutive invalid characters will be replaced with just a single underscore character.
        """
        import re
        new_name = re.sub('[^\w\_\-]+', '_', obj.name)
        if new_name == obj.name:
            return
        i = 0
        while new_name in bpy.data.objects.keys(): #while name collision with other scene objs,
            name_cut = None if i == 0 else -2  #in first loop, do not slice name.
            new_name = new_name[:name_cut] + str(i).zfill(2) #add two latters to end of obj name.
            i += 1
        obj.name = new_name


class GoB_OT_OpenFilebrowser(Operator, ImportHelper):
    bl_idname = "gob.open_filebrowser"
      
    if isMacOS:
        bl_label = "Load ZBrush.app" 
    else:
        bl_label = "Load ZBrush.exe" 

    def execute(self, context):
        """Do something with the selected file(s)."""  
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences   
        filename, extension = os.path.splitext(self.filepath)
        if 'ZBrush.exe' in self.filepath or 'ZBrush.app' in self.filepath:
            pref.zbrush_exec = self.filepath        
            bpy.ops.wm.save_userpref()
        else:
            self.filepath = ""
            print("ZBrush executable not found, try selecting it again.")

        return {'FINISHED'}


