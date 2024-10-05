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
import bmesh
import mathutils
import random
import time
from struct import unpack
import string
from bpy.types import Operator
from bpy.props import EnumProperty
from . import geometry, paths, utils, nodes


run_background_update = False
gob_import_cache = []
cached_last_edition_time = time.perf_counter()
start_time = None


class GoB_OT_import(Operator):
    bl_idname = "scene.gob_import"
    bl_label = "Import from GOZ"
    bl_description = "GoZ Import. Activate to enable Import from GoZ"    
    
    action: EnumProperty(
        items=[
            ('MANUAL', 'manual import', 'manual import'),
            ('AUTO', 'toggle automatic import', 'toggle automatic import')
        ]
    )

    def GoZit(self, pathFile): 
        if utils.prefs().performance_profiling: 
            print("\n")
            start_time = utils.profiler(time.perf_counter(), "Start Object Profiling")
            start_total_time = utils.profiler(time.perf_counter(), "...")

        utag = 0
        vertsData = []
        facesData = []
        objMat = None
        diff_texture, disp_texture, norm_texture =  None, None, None
        exists = os.path.isfile(pathFile)
        if not exists:
            if utils.prefs().debug_output:
                print(f'Cant read mesh from: {pathFile}. Skipping')
            return
        
        with open(pathFile, 'rb') as goz_file:
            goz_file.seek(36, 0)
            lenObjName = unpack('<I', goz_file.read(4))[0] - 16
            goz_file.seek(8, 1)
            obj_name = unpack('%ss' % lenObjName, goz_file.read(lenObjName))[0]
            # remove non ascii chars eg. /x 00
            objName = ''.join([letter for letter in obj_name[8:].decode('utf-8') if letter in string.printable])
            if utils.prefs().debug_output:
                print(f"Importing: {pathFile, objName}")  
            if utils.prefs().performance_profiling:                
                print(f"GoB Importing: {objName}")            
            tag = goz_file.read(4)
            
            while tag:                
                # Name
                if tag == b'\x89\x13\x00\x00':
                    if utils.prefs().debug_output:
                        print("name:", tag)
                    cnt = unpack('<L', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                    if utils.prefs().performance_profiling:  
                        start_time = utils.profiler(start_time, "____Unpack Mesh Name")

                # Vertices
                elif tag == b'\x11\x27\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Vertices:", tag)                    
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        co1 = unpack('<f', goz_file.read(4))[0]
                        co2 = unpack('<f', goz_file.read(4))[0]
                        co3 = unpack('<f', goz_file.read(4))[0]
                        vertsData.append((co1, co2, co3))

                    if utils.prefs().performance_profiling:  
                        start_time = utils.profiler(start_time, "____Unpack Mesh Vertices")
                
                # Faces
                elif tag == b'\x21\x4e\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Faces:", tag)
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
                    if utils.prefs().performance_profiling:  
                        start_time = utils.profiler(start_time, "____Unpack Mesh Faces")

                # UVs
                elif tag == b'\xa9\x61\x00\x00':  
                    if utils.prefs().debug_output:
                        print("UVs:", tag)
                    break
                # Polypainting
                elif tag == b'\xb9\x88\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Polypainting:", tag)
                    break
                # Mask
                elif tag == b'\x32\x75\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Mask:", tag)
                    break
                # Polyroups
                elif tag == b'\x41\x9c\x00\x00': 
                    if utils.prefs().debug_output:
                        print("Polyroups:", tag) 
                    break
                # End
                elif tag == b'\x00\x00\x00\x00':  
                    if utils.prefs().debug_output:
                        print("End:", tag)
                    break
                # Unknown tags
                else:
                    if utils.prefs().debug_output:
                        print("Unknown tag:{0}".format(tag))
                    if utag >= 10:
                        if utils.prefs().debug_output:
                            print("...Too many mesh tags unknown...\n")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                tag = goz_file.read(4)
                
            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "Unpack Mesh Data\n")

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
                    #update vertex positions
                    for i, v in enumerate(bm.verts):
                        v.co  = mathutils.Vector(vertsData[i])  
                    bm.to_mesh(me)   
                    bm.free()
                    #bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True) #https://docs.blender.org/api/current/bmesh.html#bmesh.update_edit_mesh

                #mesh has different vertex count
                else:              
                    me.clear_geometry() #NOTE: if this is done in edit mode we get a crash                         
                    me.from_pydata(vertsData, [], facesData)
                    #obj.data = me
            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "____create mesh") 
           
            me,_ = geometry.apply_transformation(me, is_import=True)
            # assume we have to reverse transformation from obj mode, this is needed after matrix transfomrmations      
            me.transform(obj.matrix_world.inverted())   
            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "____transform mesh")      
           
            # update mesh data after transformations to fix normals 
            if utils.prefs().debug_output:
                me.validate(verbose=False) # https://docs.blender.org/api/current/bpy.types.Mesh.html?highlight=validate#bpy.types.Mesh.validate
                if utils.prefs().performance_profiling:  
                    start_time = utils.profiler(start_time, "____validate mesh")
            
            me.update(calc_edges=True, calc_edges_loose=True)  # https://docs.blender.org/api/current/bpy.types.Mesh.html?highlight=update#bpy.types.Mesh.update
            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "____update mesh")
            
            # make object active
            obj.select_set(state=True) 
            bpy.context.view_layer.objects.active = obj
            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "____make object active")

            vertsData.clear()
            facesData.clear()

            if utils.prefs().performance_profiling:  
                start_time = utils.profiler(start_time, "Make Mesh import\n")
                
            
            utag = 0
            while tag:
                
                # UVs
                if tag == b'\xa9\x61\x00\x00':                    
                    if utils.prefs().debug_output:
                        print("Import UV: ", utils.prefs().import_uv)

                    if utils.prefs().import_uv:  
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]     # face count                        
                        bm = bmesh.new()
                        bm.from_mesh(me) 
                        bm.faces.ensure_lookup_table()

                        if me.uv_layers:
                            if utils.prefs().import_uv_name in me.uv_layers:                            
                                uv_layer = bm.loops.layers.uv.get(utils.prefs().import_uv_name)
                            else:
                                uv_layer = bm.loops.layers.uv.new(utils.prefs().import_uv_name)
                        else:
                            uv_layer = bm.loops.layers.uv.new(utils.prefs().import_uv_name) 
                        uv_layer = bm.loops.layers.uv.verify()

                        for face in bm.faces:
                            for index, loop in enumerate(face.loops):            
                                x, y = unpack('<2f', goz_file.read(8))
                                if utils.prefs().import_uv_flip_x:
                                    x = 1.0 - x
                                if utils.prefs().import_uv_flip_y:
                                    y = 1.0 - y

                                loop[uv_layer].uv = x, y


                            #uv's always have 4 coords so its required to read one more if a trinalge is in the mesh
                            # zbrush seems to always write out 4 coords            
                            if index < 3:       
                                x, y = unpack('<2f', goz_file.read(8))

                        bm.to_mesh(me)   
                        bm.free()    
                                           
                        me.update(calc_edges=True, calc_edges_loose=True)  
                        
                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "UV Map") 
                        

                # Polypainting
                elif tag == b'\xb9\x88\x00\x00': 
                    if utils.prefs().debug_output:
                        print("Import Polypaint: ", utils.prefs().import_polypaint)  

                    if utils.prefs().import_polypaint:     
                        if bpy.app.version < (3,4,0): 
                            goz_file.seek(4, 1)
                            cnt = unpack('<Q', goz_file.read(8))[0] 
                            polypaintData = []
                                            
                            for i in range(cnt):                                 
                                # Avoid error if buffer length is less than 3
                                vertex_data = goz_file.read(3)
                                if len(vertex_data) < 3:
                                    if utils.prefs().debug_output:
                                        print("error if buffer length is less than 3: ", i, vertex_data)
                                    break

                                colordata = unpack('<3B', vertex_data) # Color
                                unpack('<B', goz_file.read(1))  # Alpha
                                alpha = 1  

                                # convert color to vector                         
                                rgb = [x / 255.0 for x in colordata]    
                                rgb.reverse()                    
                                rgba = rgb + [alpha]                                          
                                polypaintData.append(tuple(rgba))                      
                                            
                            if utils.prefs().performance_profiling: 
                                start_time = utils.profiler(start_time, "Polypaint Unpack")

                            if polypaintData:                   
                                bm = bmesh.new()
                                bm.from_mesh(me)
                                bm.faces.ensure_lookup_table()
                                if me.vertex_colors:                            
                                    if utils.prefs().import_polypaint_name in me.vertex_colors: 
                                        color_layer = bm.loops.layers.color.get(utils.prefs().import_polypaint_name)
                                    else:
                                        color_layer = bm.loops.layers.color.new(utils.prefs().import_polypaint_name)                                    
                                else:
                                    color_layer = bm.loops.layers.color.new(utils.prefs().import_polypaint_name)                
                                                
                                for face in bm.faces:
                                    for loop in face.loops:
                                        # Check that the index is within the range before assigning
                                        if loop.vert.index < len(polypaintData):
                                            loop[color_layer] = polypaintData[loop.vert.index]

                                bm.to_mesh(me)                        
                                me.update(calc_edges=True, calc_edges_loose=True)  
                                bm.free()                            
                            polypaintData.clear()
                        
                        else:  # bpy.app.version >= (3,4,0):      
                            if not me.color_attributes:
                                me.color_attributes.new(utils.prefs().import_polypaint_name, 'BYTE_COLOR', 'POINT')  

                            goz_file.seek(4, 1)
                            cnt = unpack('<Q', goz_file.read(8))[0]
                            alpha = 1   
                            for i in range(cnt): 
                                # Avoid error if buffer length is less than 3
                                vertex_data = goz_file.read(3)
                                if len(vertex_data) < 3:
                                    if utils.prefs().debug_output:
                                        print("error if buffer length is less than 3: ", i, vertex_data)
                                    break
                                colordata = unpack('<3B', vertex_data) # Color
                                unpack('<B', goz_file.read(1))  # Alpha 
                                
                                # convert color to vector                         
                                rgb = [x / 255.0 for x in colordata]
                                rgb.reverse()                   
                                rgba = rgb + [alpha]   

                                # Check that the index is within the range before assigning
                                if i < len(me.attributes.active_color.data):
                                    me.attributes.active_color.data[i].color_srgb = rgba
                                                                    
                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "Polypaint Assign")


                # Mask
                elif tag == b'\x32\x75\x00\x00':   
                    if utils.prefs().debug_output:
                        print("Import Mask: ", utils.prefs().import_mask)                    
                    
                    if utils.prefs().import_mask:
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]

                        if 'mask' in obj.vertex_groups:
                            obj.vertex_groups.remove(obj.vertex_groups['mask'])
                        groupMask = obj.vertex_groups.new(name='mask')

                        for faceIndex in range(cnt):
                            weight = unpack('<H', goz_file.read(2))[0] / 65535                          
                            groupMask.add([faceIndex], 1.0-weight, 'ADD')  

                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "Mask\n")

                # Polygroups
                elif tag == b'\x41\x9c\x00\x00':   
                    if utils.prefs().debug_output:
                        print("Import Polyroups: ", utils.prefs().import_polygroups_to_vertexgroups, utils.prefs().import_polygroups_to_facemaps)
                    
                    if utils.prefs().import_polygroups:
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]     # get polygroup faces  
                        
                        polyGroupData = []
                        [polyGroupData.append(unpack('<H', goz_file.read(2))[0]) for i in range(cnt)]
                                                    
                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "____create polyGroupData")

                        # import polygroups to materials
                        if utils.prefs().import_material == 'POLYGROUPS':                                
                            # create or define active material
                            #print(polyGroupData)
                            for pgmat in set(polyGroupData):                                     
                                r = random.random()
                                g = random.random()
                                b = random.random()
                                #print("group: ", i, pgmat, r, g, b)  

                                if not str(pgmat) in bpy.data.materials:
                                    objMat = bpy.data.materials.new(str(pgmat))
                                else:
                                    objMat = bpy.data.materials[str(pgmat)]                      
                                
                                # assign material to object
                                if not objMat.name in obj.material_slots:
                                    obj.data.materials.append(objMat)
                                    objMat.use_nodes = True     
                                    rgba = (r, g, b, 1)
                                    objMat.diffuse_color = rgba
                                    objMat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = rgba

                            if utils.prefs().performance_profiling: 
                                start_time = utils.profiler(start_time, "____import_material POLYGROUPS")

                        # import polygroups to vertex groups
                        if utils.prefs().import_polygroups_to_vertexgroups:
                            for group in set(polyGroupData):
                                if str(group) in obj.vertex_groups:
                                    obj.vertex_groups.remove(obj.vertex_groups[str(group)])
                                obj.vertex_groups.new(name=str(group))  
                            
                            if utils.prefs().performance_profiling: 
                                start_time = utils.profiler(start_time, "____import_polygroups_to_vertexgroups")
                            
                        # import polygroups to face maps
                        """ if utils.prefs().import_polygroups_to_facemaps:                                
                            #wipe face maps before importing new ones due to random naming           
                            [obj.face_maps.remove(facemap) for facemap in obj.face_maps]
                            for group in set(polyGroupData):
                                obj.face_maps.new(name=str(group)) 
                            
                            if utils.prefs().performance_profiling: 
                                start_time = utils.profiler(start_time, "____import_polygroups_to_facemaps") """
                       
                        #add data to polygones
                        for i, pgmat in enumerate(polyGroupData):
                            # add materials to faces
                            if utils.prefs().import_material == 'POLYGROUPS':
                                slot = obj.material_slots[bpy.data.materials[str(pgmat)].name].slot_index
                                obj.data.polygons[i].material_index = slot     
                            
                            # add faces to facemap
                            """ if utils.prefs().import_polygroups_to_facemaps:
                                obj.face_maps.get(str(pgmat)).add([i]) """
                            
                            # add vertices to vertex groups  
                            if utils.prefs().import_polygroups_to_vertexgroups: 
                                vertexGroup = obj.vertex_groups.get(str(pgmat))
                                vertexGroup.add(list(me.polygons[i].vertices), 1.0, 'ADD')
                        
                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "____add data to polygones") 

                        polyGroupData.clear()

                        if utils.prefs().performance_profiling: 
                            start_time = utils.profiler(start_time, "Polyroups\n")

                # End
                elif tag == b'\x00\x00\x00\x00': 
                    break
                
                # Diffuse Texture 
                elif tag == b'\xc9\xaf\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Diff map:", tag)
                    texture_name = (obj.name + utils.prefs().import_diffuse_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    diffName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    if utils.prefs().debug_output:
                        print(diffName.decode('utf-8'))
                    img = bpy.data.images.load(diffName.strip().decode('utf-8'), check_existing=True) 
                    img.name = texture_name                                        
                    img.reload()
                    
                    if not texture_name in bpy.data.textures:
                        txtDiff = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDiff.image = img            
                    diff_texture = img
  
                # Displacement Texture 
                elif tag == b'\xd9\xd6\x00\x00':  
                    if utils.prefs().debug_output:
                        print("Disp map:", tag)
                    texture_name = (obj.name + utils.prefs().import_displace_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    dispName = unpack('%ss' % cnt, goz_file.read(cnt))[0]                    
                    if utils.prefs().debug_output:
                        print(dispName.decode('utf-8'))                    
                    img = bpy.data.images.load(dispName.strip().decode('utf-8'), check_existing=True)  
                    img.name = texture_name                                       
                    img.reload()

                    if not texture_name in bpy.data.textures:
                        txtDisp = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtDisp.image = img
                    disp_texture = img

                # Normal Map Texture
                elif tag == b'\x51\xc3\x00\x00':   
                    if utils.prefs().debug_output:
                        print("Normal map:", tag)
                    texture_name = (obj.name + utils.prefs().import_normal_suffix)
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    normName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    if utils.prefs().debug_output:
                        print(normName.decode('utf-8'))
                    img = bpy.data.images.load(normName.strip().decode('utf-8'), check_existing=True) 
                    img.name = texture_name                                       
                    img.reload()
                    
                    if not texture_name in bpy.data.textures:
                        txtNorm = bpy.data.textures.new(texture_name, 'IMAGE')
                        txtNorm.image = img
                    norm_texture = img
                
                # Unknown tags
                else: 
                    if utils.prefs().debug_output:
                        print("Unknown tag:{0}".format(tag))
                    if utag >= 10:
                        if utils.prefs().debug_output:
                            print("...Too many object tags unknown...\n")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)

                tag = goz_file.read(4)
                
            if utils.prefs().performance_profiling:                
                start_time = utils.profiler(start_time, "Textures")
            
            # MATERIALS
            if utils.prefs().import_material:
                if utils.prefs().debug_output:
                    print("Import Material: ", utils.prefs().import_material)

                # POLYPAINT
                if utils.prefs().import_material == 'POLYPAINT':                    
                    if utils.prefs().import_polypaint_name in me.color_attributes:                                                   
                        if len(obj.material_slots) > 0:
                            if obj.material_slots[0].material is not None:
                                objMat = obj.material_slots[0].material
                            else:
                                objMat = bpy.data.materials.new(objName)
                                obj.material_slots[0].material = objMat
                        else:
                            objMat = bpy.data.materials.new(objName)
                            obj.data.materials.append(objMat)

                        nodes.create_material_node(objMat, diff_texture, norm_texture, disp_texture) 

                # TEXTURES    
                elif utils.prefs().import_material == 'TEXTURES':                               
                    if len(obj.material_slots) > 0:
                        if obj.material_slots[0].material is not None:
                            objMat = obj.material_slots[0].material
                        else:
                            objMat = bpy.data.materials.new(objName)
                            obj.material_slots[0].material = objMat
                    else:
                        objMat = bpy.data.materials.new(objName)
                        obj.data.materials.append(objMat)
                    
                    print("create material node:", objMat)
                    nodes.create_material_node(objMat, diff_texture, norm_texture, disp_texture)  


            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "Material Node")                

            # #apply face maps to sculpt mode face sets
            if utils.prefs().apply_facemaps_to_facesets and  bpy.app.version > (2, 82, 7):                
                bpy.ops.object.mode_set(mode='SCULPT')                 
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type in {'VIEW_3D'}: 
                            override = {'window': window, 'screen': screen, 'area': area}
                            bpy.ops.sculpt.face_sets_init(override, mode='FACE_MAPS')   
                            break                   
                if utils.prefs().performance_profiling:                
                    start_time = utils.profiler(start_time, "Init Face Sets")

                # reveal all mesh elements (after the override for the face maps the elements without faces are hidden)                                 
                bpy.ops.object.mode_set(mode='EDIT') 
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type in {'VIEW_3D'}:
                            override = {'window': window, 'screen': screen, 'area': area}
                            bpy.ops.mesh.reveal(override)
                            break  

                if utils.prefs().performance_profiling:                
                    start_time = utils.profiler(start_time, "Reveal Mesh Elements")
                                           
            if utils.prefs().performance_profiling: 
                print(30*"-") 
                utils.profiler(start_total_time, "Object Import Time")  
                print(30*"-")                
        return
             

    def execute(self, context):   
        
        if utils.prefs().custom_pixologoc_path:
            paths.PATH_GOZ =  utils.prefs().pixologoc_path  

        global gob_import_cache
        goz_obj_paths = []
        try:
            with open(os.path.join(f"{paths.PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt"), 'rt') as goz_objs_list:
                for line in goz_objs_list:
                    goz_obj_paths.append(line.strip() + '.GoZ')
        except PermissionError:
            if utils.prefs().debug_output:
                print("GoB: GoZ_ObjectList already in use! Try again Later")
        except Exception as e:
            print(e)

        # Goz wipes this file before each export so it can be used to reset the import cache
        if not goz_obj_paths:
            if utils.prefs().debug_output:
                self.report({'INFO'}, message="GoB: No goz files in GoZ_ObjectList") 
            return{'CANCELLED'}

        currentContext = 'OBJECT'
        if context.object:
            if context.object.mode != 'EDIT':
                currentContext = context.object.mode
                #print("currentContext: ", currentContext)
                # ! cant get proper context from timers for now to change mode: 
                # https://developer.blender.org/T62074
                bpy.ops.object.mode_set(mode=currentContext) 
            else:
                bpy.ops.object.mode_set(mode='OBJECT')


        if utils.prefs().performance_profiling: 
            print("\n", 100*"=")
            start_time = utils.profiler(time.perf_counter(), "GoB: Start Import Profiling")             
            print(100*"-") 

        wm = context.window_manager
        wm.progress_begin(0,100)
        step =  100  / len(goz_obj_paths)
        for i, ztool_path in enumerate(goz_obj_paths):          
            if ztool_path not in gob_import_cache:
                gob_import_cache.append(ztool_path)
                self.GoZit(ztool_path)
            wm.progress_update(step * i)
        wm.progress_end()
        if utils.prefs().debug_output:
            self.report({'INFO'}, "GoB: Imoprt cycle finished")

        if utils.prefs().performance_profiling:  
            start_time = utils.profiler(start_time, "GoB: Total Import Time")            
            print(100*"=")
        return{'FINISHED'}

    
    def invoke(self, context, event):  
        if utils.prefs().debug_output:
            print("ACTION: ", self.action) 

        if self.action == 'MANUAL':
            run_import_manually()
            return{'FINISHED'}

        if self.action == 'AUTO':    
            if utils.prefs().import_method == 'AUTOMATIC':
                global run_background_update
                if run_background_update:
                    if bpy.app.timers.is_registered(run_import_periodically):
                        bpy.app.timers.unregister(run_import_periodically)
                        if utils.prefs().debug_output:
                            print('Disabling GOZ background listener')
                    run_background_update = False
                else:
                    if not bpy.app.timers.is_registered(run_import_periodically):
                        global cached_last_edition_time
                        GoZ_ObjectList = os.path.join(f"{paths.PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt")
                        try:
                            cached_last_edition_time = os.path.getmtime(GoZ_ObjectList)
                        except Exception:
                            f = open(GoZ_ObjectList, 'x')
                            f.close()
                        bpy.app.timers.register(run_import_periodically, persistent=True)
                        if utils.prefs().debug_output:
                            print('Enabling GOZ background listener')
                    run_background_update = True
            elif run_background_update:
                if bpy.app.timers.is_registered(run_import_periodically):
                    bpy.app.timers.unregister(run_import_periodically)
                    print('Disabling GOZ background listener')
                run_background_update = False
            return{'FINISHED'}


def run_import_periodically():
    # print("Runing timers update check")
    global cached_last_edition_time, run_background_update

    try:
        file_edition_time = os.path.getmtime(os.path.join(f"{paths.PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt"))
        #print("file_edition_time: ", file_edition_time, end='\n\n')
    except Exception as e:
        print(e)
        run_background_update = False
        if bpy.app.timers.is_registered(run_import_periodically):
            bpy.app.timers.unregister(run_import_periodically)
        return utils.prefs().import_timer
    
    if file_edition_time > cached_last_edition_time:
        cached_last_edition_time = file_edition_time        
        bpy.ops.scene.gob_import() #only call operator update is found (executing operatros is slow)
    else:       
        global gob_import_cache  
        if gob_import_cache:  
            if utils.prefs().debug_output:   
                print("GOZ: clear import cache", file_edition_time - cached_last_edition_time)
            gob_import_cache.clear()   #reset import cache
        else:
            if utils.prefs().debug_output:
                print("GOZ: Nothing to update", file_edition_time - cached_last_edition_time)
            else:
                pass    
        return utils.prefs().import_timer       
    
    if not run_background_update and bpy.app.timers.is_registered(run_import_periodically):
        bpy.app.timers.unregister(run_import_periodically)
        
    return utils.prefs().import_timer


def run_import_manually():  
    gob_import_cache.clear() 
    bpy.ops.scene.gob_import() #only call operator update is found (executing operatros is slow)  
    



