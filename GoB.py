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
import bmesh
import mathutils
import math
import time
import os
from struct import pack, unpack
from copy import deepcopy
import string



if os.path.isfile("C:/Users/Public/Pixologic/GoZBrush/GoZBrushFromApp.exe"):
    PATHGOZ = "C:/Users/Public/Pixologic"
    FROMAPP = "GoZBrushFromApp.exe"
elif os.path.isfile("/Users/Shared/Pixologic/GoZBrush/GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"):
    PATHGOZ = "/Users/Shared/Pixologic"
    FROMAPP = "GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"
else:
    PATHGOZ = False


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
class GoB_OT_import(bpy.types.Operator):
    bl_idname = "scene.gob_import"
    bl_label = "GOZ import"
    bl_description = "GOZ import background listener"
    
    
    def GoZit(self, pathFile):     
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
        
        if pref.performance_profiling: 
            print("\n", 100*"=")
            start_time = profiler(time.time(), "Start Import Profiling")
            start_total_time = profiler(time.time(), "")

        scn = bpy.context.scene
        utag = 0
        vertsData = []
        facesData = []
        objMat = None
        diff = False
        disp = False
        norm = False
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
                #print("\ntag 0:", tag)
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
                me = bpy.data.meshes.new(objName)  #create empty mesh  
                me.from_pydata(vertsData, [], facesData)
                obj = bpy.data.objects.new(objName, me)
                # link object to active collection
                bpy.context.view_layer.active_layer_collection.collection.objects.link(obj)          

            # object already exist
            else:
                #mesh has same vertex count
                if len(bpy.data.objects[objName].data.vertices) == len(vertsData): 
                    obj = bpy.data.objects[objName]
                    me = obj.data
                    bm = bmesh.new()
                    bm.from_mesh(me)
                    bm.faces.ensure_lookup_table() 
                    #udpate vertex positions
                    for i, v in enumerate(bm.verts):
                        v.co = vertsData[i]                    
                    bm.to_mesh(me)        
                    bm.free() 
                #mesh has different vertex count
                else:  
                    obj = bpy.data.objects[objName]                    
                    obj.data.clear_geometry()
                    me = obj.data                              
                    me.from_pydata(vertsData, [], facesData)
                    obj.data = me
            
            # update mesh data after transformations to fix normals     
            me.update(calc_edges=True, calc_edges_loose=True)    
            me,_ = apply_transformation(me, is_import=True)

            #obj.data.transform(obj.matrix_world.inverted())     # assume we have to reverse transformation from obj mode #TODO why do we do this?
            obj.select_set(True)      # make object active
            bpy.context.view_layer.objects.active = obj
            utag = 0  #TODO: why do we need this? 
            vertsData.clear()
            facesData.clear()

            if pref.performance_profiling:  
                start_time = profiler(start_time, "Make Mesh")
                
            
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
                    create_node_material(objMat, pref)  
                    
                elif pref.import_material == 'TEXTURES':
                    create_node_material(objMat, pref)  
                    
                elif pref.import_material == 'POLYGROUPS':
                    create_node_material(objMat, pref)  
          
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Material Node")


            while tag:
                #print("\ntag 00:", tag)
                # UVs
                if tag == b'\xa9\x61\x00\x00':
                    print("Import UV: ", pref.import_uv)
                    if pref.import_uv:  
                        #print("UVs:", tag)
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]     # face count.. 
                        
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
                            for i, loop in enumerate(face.loops):
                                x,y = unpack('<2f', goz_file.read(8)) 
                                loop[uv_layer].uv = x, 1.0-y

                        bm.to_mesh(me)   
                        bm.free()                       
                        me.update(calc_edges=True, calc_edges_loose=True)  
                    else:
                        break
                    if pref.performance_profiling: 
                        start_time = profiler(start_time, "UV Map")

                # Polypainting
                elif tag == b'\xb9\x88\x00\x00': 
                    print("Import Polypaint: ", pref.import_polypaint)  
                    if pref.import_polypaint:
                        print("Polypainting:", tag)
                    else:
                        break
                    polypaintData = []
                    min = 255 #TODO: why is this called min? what is this?
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]                   
                    
                    for i in range(cnt): 
                        data = unpack('<3B', goz_file.read(3))
                        
                        unpack('<B', goz_file.read(1))  # Alpha
                        if data[0] < min:
                            min = data[0]   #TODO: assing data to min, what is this data?                          
                        else:                            
                            #print("polypaint min: ", min, data[0])  
                            pass
                        alpha = 1                        

                        #convert color to vector                         
                        rgb = [x / 255.0 for x in data]    
                        rgb.reverse()                    
                        rgba = rgb + [alpha]                                          
                        polypaintData.append(tuple(rgba))                      
                    
                    if pref.performance_profiling: 
                        start_time = profiler(start_time, "Polypaint Unpack")

                    if min < 250: #TODO: whats this 250?                      
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


                # Mask
                elif tag == b'\x32\x75\x00\x00':   
                    print("Import Mask: ", pref.import_mask)
                    
                    if pref.import_mask:
                        #print("Mask:", tag)
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
                        break

                # Polyroups
                elif tag == b'\x41\x9c\x00\x00':   
                    print("Import Polyroups: ", pref.import_polygroups_to_vertexgroups, pref.import_polygroups_to_facemaps)
                    
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
                                fm = obj.face_maps.new(name=str(group))
                                facemapsData.append(group)
                            else:
                                fm = obj.face_maps[str(group)]
                            fm.add([i])     # add faces to facemap
                    try:
                        obj.vertex_groups.remove(obj.vertex_groups.get('0'))
                    except:
                        pass

                    try:
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
                
                # Diff map 
                elif tag == b'\xc9\xaf\x00\x00':  
                    #print("Diff map:", tag)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    diffName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(diffName.decode('utf-8'))
                    img = bpy.data.images.load(diffName.strip().decode('utf-8'))
                    diff = True

                    prefix = obj.name
                    suffix = pref.imp_tex_diffuse_suffix
                    texture_name = (prefix + "_" + suffix)
                    if not texture_name in bpy.data.textures:
                        txtDiff = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDiff.image = img
                        # me.uv_textures[0].data[0].image = img

                # Disp map 
                elif tag == b'\xd9\xd6\x00\x00':  
                    #print("Disp map:", tag)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    dispName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(dispName.decode('utf-8'))
                    img = bpy.data.images.load(dispName.strip().decode('utf-8'))
                    disp = True
                    
                    prefix = obj.name
                    suffix = pref.imp_tex_displace_suffix
                    texture_name = (prefix + "_" + suffix)
                    if not texture_name in bpy.data.textures:
                        txtDisp = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDisp.image = img
                
                # Normal map
                elif tag == b'\x51\xc3\x00\x00':   
                    #print("Normal map:", tag)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    normName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(normName.decode('utf-8'))
                    img = bpy.data.images.load(normName.strip().decode('utf-8'))
                    norm = True
                    
                    prefix = obj.name
                    suffix = pref.imp_tex_normal_suffix
                    texture_name = (prefix + "_" + suffix)
                    if not texture_name in bpy.data.textures:
                        txtNorm = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtNorm.image = img
                        txtNorm.use_normal_map = True
                
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

            # #apply face maps to sculpt mode face sets
            if pref.apply_facemaps_to_facesets and  bpy.app.version > (2, 82, 7):
                current_mode = bpy.context.mode
                bpy.ops.object.mode_set(bpy.context.copy(), mode='SCULPT')
                
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            override = bpy.context.copy()
                            override = {'window': window, 'screen': screen, 'area': area}
                            bpy.ops.sculpt.face_sets_init(override, mode='FACE_MAPS')
                            break                                 

                if pref.performance_profiling: 
                    profiler(start_time, "Face Maps")
                    print(30*"-")
                    profiler(start_total_time, "Total Import Time")  
                    print(30*"=")       
       
        return
             


    def execute(self, context):
        goz_obj_paths = []
        with open(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt", 'rt') as goz_objs_list:
            for line in goz_objs_list:
                goz_obj_paths.append(line.strip() + '.GoZ')

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


def create_node_material(mat, pref):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    output_node = nodes.get('Principled BSDF')    
    
    #check if we have a vc node assigned 
    vcol_node = False   
    for node in nodes:
        if node.bl_idname == 'ShaderNodeAttribute':
            if pref.import_polypaint_name in node.attribute_name:
                vcol_node = nodes.get(node.name)  
    #create new node if none is assigned/exists
    if not vcol_node:
        vcol_node = nodes.new('ShaderNodeAttribute')
        vcol_node.location = -300, 200
        vcol_node.attribute_name = pref.import_polypaint_name    
        mat.node_tree.links.new(output_node.inputs[0], vcol_node.outputs[0])
    

           
def apply_transformation(me, is_import=True): 
    pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
    mat_transform = None

    # TODO: do we add scaling here?
    
    #import
    if pref.flip_up_axis:  # fixes bad mesh orientation for some people
        if pref.flip_forward_axis:
            if is_import:
                me.transform(mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]))
                me.flip_normals()
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)])
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]))
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)])

    else:
        if pref.flip_forward_axis:            
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]))
                me.flip_normals()
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)])
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]))
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., -1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)])
    return me, mat_transform
                
def profiler(start_time=0, string=None):               
    
    elapsed = time.time()
    print("{:.4f}".format(elapsed-start_time), "<< ", string)  
    start_time = time.time()
    return start_time  

def run_import_periodically():
    # print("Runing timers update check")
    global cached_last_edition_time, run_background_update

    try:
        file_edition_time = os.path.getmtime(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt")
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


class GoB_OT_export(bpy.types.Operator):
    bl_idname = "scene.gob_export"
    bl_label = "Export to Zbrush"
    bl_description = "Export to Zbrush"
    
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

    @staticmethod
    def make_polygroups(obj, pref):        
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        
        # mask
        if pref.export_mask:
            print("Export Mask: ", pref.export_mask)

        print("Export polygroups: ", pref.export_polygroups)
        if pref.export_polygroups == 'NONE': 
            pass 
                  
        #vertex weights to polygroups
        elif pref.export_polygroups == 'VERTEX_GROUPS':
            pass

        #face maps to polygroups       
        elif pref.export_polygroups == 'FACE_MAPS':
            pass
            """ 
            for facemap in obj.face_maps:
                #print("map name and index: ", facemap.name, facemap.index)
                if not facemap:
                    continue            
                verts = [v for index, map in enumerate(obj.data.face_maps[0].data)
                                if map.value == facemap.index  
                                    for f in obj.data.polygons 
                                        if f.index==index
                                            for v in f.vertices]                                                                        
                verts = list(set(verts)) 
                if len(verts):
                    vg = obj.vertex_groups.get(facemap.name)                
                    if vg is None:               
                        vg = obj.vertex_groups.new(name=facemap.name) 
                        vg.add(verts, 1.0, 'ADD') 
            """

        #materials to polygroups
        elif pref.export_polygroups == 'MATERIALS':
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
            for vertexGroup in obj.vertex_groups:
                #obj.vertex_groups.remove(vertexGroup)
                pass

    def exportGoZ(self, path, scn, obj, pathImport):
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences

        if pref.performance_profiling: 
            print("\n", 100*"=")
            start_time = profiler(time.time(), "Start Export Profiling")
            start_total_time = profiler(time.time(), "")
        
        # TODO: when linked system is finalized it could be possible to provide
        #  a option to modify the linked object. for now a copy
        #  of the linked object is created to goz it
        if bpy.context.object.type == 'MESH':
            if bpy.context.object.library:
                new_ob = obj.copy()
                new_ob.data = obj.data.copy()
                scn.collection.objects.link(new_ob)
                new_ob.select_set(state=True)
                obj.select_set(state=False)
                bpy.context.view_layer.objects.active = new_ob

                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Linked Object")

        self.make_polygroups(obj, pref)                
        me = self.apply_modifiers(obj, pref)
        me.calc_loop_triangles()
        me, mat_transform = apply_transformation(me, is_import=False)

        if pref.performance_profiling: 
            start_time = profiler(start_time, "Make Mesh")


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
                modif_coo = obj.matrix_world @ vert.co
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
                uvdata = me.uv_layers[0].data
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
            for vertexGroup in obj.vertex_groups:
                if vertexGroup.name.lower() == 'mask':
                    goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*2+16))
                    goz_file.write(pack('<Q', numVertices))
                    for i in range(numVertices):
                        try:
                            goz_file.write(pack('<H', int((1.0 - vertexGroup.weight(i)) * 65535)))
                        except:
                            goz_file.write(pack('<H', 255))
            
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Mask")

           
           
            # --Polygroups--                        
            goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
            goz_file.write(pack('<I', numFaces*2+16))
            goz_file.write(pack('<Q', numFaces)) 

            if obj.face_maps.items is not None:  
                import random
                #create a color for each facemap (0xffff)
                colorData=[]
                for fm in obj.face_maps:
                    randcolor = "%5x" % random.randint(0x1111, 0xFFFF)
                    color = int(randcolor, 16)
                    colorData.append(color)

                print("import face maps")
                for index, map in enumerate(me.face_maps[0].data):
                    if map.value >= 0:
                        goz_file.write(pack('<H', colorData[map.value]))  
                    else: #face without facemaps (value = -1)
                        goz_file.write(pack('<H', 0))
                        
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write FaceMaps to Polygroups") 
            
            #OLD METHOD
            """  vertWeight = []   
            for i in range(len(me.vertices)):
                vertWeight.append([])
                for group in me.vertices[i].groups:
                    try:
                        if group.weight == 1.0 and obj.vertex_groups[group.group].name.lower() != 'mask':
                            vertWeight[i].append(group.weight)
                            #print("group, weight", group.group, group.weight)
                    except:
                        print('error reading vertex group data')
                        
            #print("vertWeight: ", len(vertWeight), vertWeight)

            for face in me.polygons:
                group = []
                for vert in face.vertices:
                    group.extend(vertWeight[vert])
                    #print("index: ", face.index, vert, vertWeight[vert])
                group.sort()
                group.reverse()
                tmp = {}
                groupVal = int(0)

                for val in group:
                    #print("val0: ", val)
                    if val not in tmp:
                        tmp[val] = 1
                    else:
                        tmp[val] += 1

                        #print("val: ", int(val), tmp[val], len(face.vertices))
                        if tmp[val] == len(face.vertices):
                            groupVal = int(val)
                            #print("groupVal", groupVal)
                            break
                                    
                if obj.vertex_groups.items() != []:
                    groupName = obj.vertex_groups[groupVal].name
                    #print("groupName 00: ", face.index , groupName, "groupVal: ", groupVal)

                    if groupName.lower() == 'mask':
                        goz_file.write(pack('<H', 0))
                    else:
                        groupName = obj.vertex_groups[1].index*numrand
                        goz_file.write(pack('<H', groupName))
                        print("groupName 01: ", face.index, obj.vertex_groups[1].index)
                else:
                    goz_file.write(pack('<H', 0)) 
                    print("groupName 02: ", face.index , groupName)
                #print("\n")
           
                print("group:", face.index, len(group), group)

                    
            if pref.performance_profiling: 
                start_time = profiler(start_time, "Write Polygroups") """





            # Diff, disp and norm maps
            diff = 0
            disp = 0
            norm = 0
            GoBmat = False
            for matslot in obj.material_slots:
                if matslot.material:
                    GoBmat = matslot
                    break
            # if GoBmat:
            #     for texslot in GoBmat.material.texture_slots:
            #         if texslot:
            #             if texslot.texture:
            #                 if texslot.texture.type == 'IMAGE' and texslot.texture_coords == 'UV' and texslot.texture.image:
            #                     if texslot.use_map_color_diffuse:
            #                         diff = texslot
            #                     if texslot.use_map_displacement:
            #                         disp = texslot
            #                     if texslot.use_map_normal:
            #                         norm = texslot
            formatRender = scn.render.image_settings.file_format
            scn.render.image_settings.file_format = 'BMP'

            if diff:
                name = diff.texture.image.filepath.replace('\\', '/')
                name = name.rsplit('/')[-1]
                name = name.rsplit('.')[0]
                if len(name) > 5:
                    if name[-5:] == "_TXTR":
                        name = path + '/GoZProjects/Default/' + name + '.bmp'
                    else:
                        name = path + '/GoZProjects/Default/' + name + '_TXTR.bmp'
                diff.texture.image.save_render(name)
                print(name)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xc9, 0xaf, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write diff")

            if disp:
                name = disp.texture.image.filepath.replace('\\', '/')
                name = name.rsplit('/')[-1]
                name = name.rsplit('.')[0]
                if len(name) > 3:
                    if name[-3:] == "_DM":
                        name = path + '/GoZProjects/Default/' + name + '.bmp'
                    else:
                        name = path + '/GoZProjects/Default/' + name + '_DM.bmp'
                disp.texture.image.save_render(name)
                print(name)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xd9, 0xd6, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write disp")

            if norm:
                name = norm.texture.image.filepath.replace('\\', '/')
                name = name.rsplit('/')[-1]
                name = name.rsplit('.')[0]
                if len(name) > 3:
                    if name[-3:] == "_NM":
                        name = path + '/GoZProjects/Default/' + name + '.bmp'
                    else:
                        name = path + '/GoZProjects/Default/' + name + '_NM.bmp'
                norm.texture.image.save_render(name)
                print(name)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0x51, 0xc3, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
                
                if pref.performance_profiling: 
                    start_time = profiler(start_time, "Write norm")

            # end
            scn.render.image_settings.file_format = formatRender
            goz_file.write(pack('16x'))
            
            if pref.performance_profiling: 
                profiler(start_time, "Write Textures")
                print(30*"-")
                profiler(start_total_time, "Total Export Time")
                print(30*"=")

        bpy.data.meshes.remove(me)
        return

    def execute(self, context):
        exists = os.path.isfile(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt")
        if not exists:
            print(f'Cant find: {f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt"}. Check your Zbrush GOZ installation')
            return {"CANCELLED"}
          
        currentContext = 'OBJECT'
        if context.object and context.object.mode != 'OBJECT':            
            currentContext = context.object.mode
            bpy.ops.object.mode_set(bpy.context.copy(), mode='OBJECT')
        with open(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt", 'wt') as GoZ_ObjectList:
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    self.escape_object_name(obj)
                    self.exportGoZ(PATHGOZ, context.scene, obj, f'{PATHGOZ}/GoZProjects/Default')
                    with open( f"{PATHGOZ}/GoZProjects/Default/{obj.name}.ztn", 'wt') as ztn:
                        ztn.write(f'{PATHGOZ}/GoZProjects/Default/{obj.name}')
                    GoZ_ObjectList.write(f'{PATHGOZ}/GoZProjects/Default/{obj.name}\n')

        global cached_last_edition_time
        cached_last_edition_time = os.path.getmtime(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt")
        os.system(f"{PATHGOZ}/GoZBrush/{FROMAPP}")
        
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




