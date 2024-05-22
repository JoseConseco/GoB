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
import bmesh
import mathutils
import random
import time
from struct import pack, unpack
import string
from bpy.types import Operator
from bpy.props import EnumProperty
from bpy.app.translations import pgettext_iface as iface_

from . import geometry, output, paths, utils, gob_import, nodes


#create GoB paths when loading the addon
isMacOS, PATH_GOB, PATH_BLENDER, PATH_GOZ_PIXOLOGIC, PATH_GOZ_MAXON = paths.gob_init_os_paths()
print("PATH_GOZ_PIXOLOGIC: ", PATH_GOZ_PIXOLOGIC)
print("PATH_GOZ_MAXON: ", PATH_GOZ_MAXON)

run_background_update = False
icons = None
cached_last_edition_time = time.perf_counter()
last_cache = 0
preview_collections = {}
gob_import_cache = []

def draw_goz_buttons(self, context):
    global run_background_update, icons
    if context.region.alignment == 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)

        icons = preview_collections["main"]

        if utils.prefs().show_button_text:
            row.operator(operator="scene.gob_export_button", text="Export", emboss=True, icon_value=icons["GOZ_SEND"].icon_id)
            if run_background_update:
                row.operator(operator="scene.gob_import", text=iface_("Import", None), emboss=True, depress=True, icon_value=icons["GOZ_SYNC_ENABLED"].icon_id).action = 'AUTO'
            else:
                row.operator(operator="scene.gob_import", text=iface_("Import", None), emboss=True, depress=False, icon_value=icons["GOZ_SYNC_DISABLED"].icon_id).action = 'AUTO'
            row.operator(operator="scene.gob_import", text="Manual", emboss=True, depress=False, icon='IMPORT').action = 'MANUAL'
        else:
            row.operator(operator="scene.gob_export_button", text="", emboss=True, icon_value=icons["GOZ_SEND"].icon_id)
            if run_background_update:
                row.operator(operator="scene.gob_import", text="", emboss=True, depress=True, icon_value=icons["GOZ_SYNC_ENABLED"].icon_id).action = 'AUTO'
            else:
                row.operator(operator="scene.gob_import", text="", emboss=True, depress=False, icon_value=icons["GOZ_SYNC_DISABLED"].icon_id).action = 'AUTO'
            row.operator(operator="scene.gob_import", text="", emboss=True, depress=False, icon='IMPORT').action = 'MANUAL'

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
            start_time = output.profiler(time.perf_counter(), "Start Object Profiling")
            start_total_time = output.profiler(time.perf_counter(), "...")

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
                        start_time = output.profiler(start_time, "____Unpack Mesh Name")

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
                        start_time = output.profiler(start_time, "____Unpack Mesh Vertices")
                
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
                        start_time = output.profiler(start_time, "____Unpack Mesh Faces")

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
                start_time = output.profiler(start_time, "Unpack Mesh Data\n")

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
                start_time = output.profiler(start_time, "____create mesh") 
           
            me,_ = geometry.apply_transformation(me, is_import=True)
            # assume we have to reverse transformation from obj mode, this is needed after matrix transfomrmations      
            me.transform(obj.matrix_world.inverted())   
            if utils.prefs().performance_profiling:  
                start_time = output.profiler(start_time, "____transform mesh")      
           
            # update mesh data after transformations to fix normals 
            if utils.prefs().debug_output:
                me.validate(verbose=False) # https://docs.blender.org/api/current/bpy.types.Mesh.html?highlight=validate#bpy.types.Mesh.validate
                if utils.prefs().performance_profiling:  
                    start_time = output.profiler(start_time, "____validate mesh")
            
            me.update(calc_edges=True, calc_edges_loose=True)  # https://docs.blender.org/api/current/bpy.types.Mesh.html?highlight=update#bpy.types.Mesh.update
            if utils.prefs().performance_profiling:  
                start_time = output.profiler(start_time, "____update mesh")
            
            # make object active
            obj.select_set(state=True) 
            bpy.context.view_layer.objects.active = obj
            if utils.prefs().performance_profiling:  
                start_time = output.profiler(start_time, "____make object active")

            vertsData.clear()
            facesData.clear()

            if utils.prefs().performance_profiling:  
                start_time = output.profiler(start_time, "Make Mesh import\n")
                
            
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
                                loop[uv_layer].uv = x, 1.0-y
                            #uv's always have 4 coords so its required to read one more if a trinalge is in the mesh
                            # zbrush seems to always write out 4 coords            
                            if index < 3:       
                                x, y = unpack('<2f', goz_file.read(8))

                        bm.to_mesh(me)   
                        bm.free()    
                                           
                        me.update(calc_edges=True, calc_edges_loose=True)  
                        
                        if utils.prefs().performance_profiling: 
                            start_time = output.profiler(start_time, "UV Map") 
                        

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
                                    print("error if buffer length is less than 3: ", v, vertex_data)
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
                                start_time = output.profiler(start_time, "Polypaint Unpack")

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
                                    print("error if buffer length is less than 3: ", v, vertex_data)
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
                            start_time = output.profiler(start_time, "Polypaint Assign")


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
                            start_time = output.profiler(start_time, "Mask\n")

                # Polygroups
                elif tag == b'\x41\x9c\x00\x00':   
                    if utils.prefs().debug_output:
                        print("Import Polyroups: ", utils.prefs().import_polygroups_to_vertexgroups, utils.prefs().import_polygroups_to_facemaps)
                    
                    if utils.prefs().import_polygroups:
                        polyGroupData = []
                        goz_file.seek(4, 1)
                        cnt = unpack('<Q', goz_file.read(8))[0]     # get polygroup faces  
                        #""" 
                        for i in range(cnt):    # faces of each polygroup      
                            #group = unpack('<H', goz_file.read(2))[0]   
                            polyGroupData.append(unpack('<H', goz_file.read(2))[0]) 
                        #"""
                        #[polyGroupData.append(unpack('<H', goz_file.read(2))[0]) for i in range(cnt)]
                                                    
                        if utils.prefs().performance_profiling: 
                            start_time = output.profiler(start_time, "____create polyGroupData")

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
                                start_time = output.profiler(start_time, "____import_material POLYGROUPS")

                        # import polygroups to vertex groups
                        if utils.prefs().import_polygroups_to_vertexgroups:
                            for group in set(polyGroupData):
                                if str(group) in obj.vertex_groups:
                                    obj.vertex_groups.remove(obj.vertex_groups[str(group)])
                                obj.vertex_groups.new(name=str(group))  
                            
                            if utils.prefs().performance_profiling: 
                                start_time = output.profiler(start_time, "____import_polygroups_to_vertexgroups")
                            
                        # import polygroups to face maps
                        """ if utils.prefs().import_polygroups_to_facemaps:                                
                            #wipe face maps before importing new ones due to random naming           
                            [obj.face_maps.remove(facemap) for facemap in obj.face_maps]
                            for group in set(polyGroupData):
                                obj.face_maps.new(name=str(group)) 
                            
                            if utils.prefs().performance_profiling: 
                                start_time = output.profiler(start_time, "____import_polygroups_to_facemaps") """
                       
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
                            start_time = output.profiler(start_time, "____add data to polygones") 

                        polyGroupData.clear()

                        if utils.prefs().performance_profiling: 
                            start_time = output.profiler(start_time, "Polyroups\n")

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
                start_time = output.profiler(start_time, "Textures")
            
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
                start_time = output.profiler(start_time, "Material Node")                

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
                    start_time = output.profiler(start_time, "Init Face Sets")

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
                    start_time = output.profiler(start_time, "Reveal Mesh Elements")
                                           
            if utils.prefs().performance_profiling: 
                print(30*"-") 
                output.profiler(start_total_time, "Object Import Time")  
                print(30*"-")                
        return
             

    def execute(self, context):   
        global PATH_GOZ_PIXOLOGIC     
        if utils.prefs().custom_pixologoc_path:
            PATH_GOZ_PIXOLOGIC =  utils.prefs().pixologoc_path  

        global gob_import_cache
        goz_obj_paths = []
        try:
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_ObjectList.txt"), 'rt') as goz_objs_list:
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
            start_time = output.profiler(time.perf_counter(), "GoB: Start Import Profiling")             
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
            start_time = output.profiler(start_time, "GoB: Total Import Time")            
            print(100*"=")
        return{'FINISHED'}

    
    def invoke(self, context, event):  
        if utils.prefs().debug_output:
            print("ACTION: ", self.action) 

        if self.action == 'MANUAL':
            gob_import.run_import_manually()
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
                        PATH_GOZ = PATH_GOZ_PIXOLOGIC
                        GoZ_ObjectList = os.path.join(f"{PATH_GOZ}/GoZBrush/GoZ_ObjectList.txt")
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



class GoB_OT_export(Operator):
    bl_idname = "scene.gob_export"
    bl_label = "Export to ZBrush"
    bl_description = "Export selected Objects to ZBrush"

    as_tool: bpy.props.BoolProperty(
        name="Export As Tool",
        description="Export as a tool instead of a subtool",
        default=False,
    )
    
    @classmethod
    def poll(cls, context):              
        return geometry.export_poll(cls, context)
    

    def exportGoZ(self, path, scn, obj, pathImport):      
        PATH_PROJECT = os.path.join(utils.prefs().project_path).replace("\\", "/")
        if utils.prefs().performance_profiling: 
            print("\n", 100*"=")
            start_time = output.profiler(time.perf_counter(), "Export Profiling: " + obj.name)
            start_total_time = output.profiler(time.perf_counter(), 80*"=")

        me = geometry.apply_modifiers(obj)
        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh apply_modifiers")

        me.calc_loop_triangles()
        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh calc_loop_triangles")

        me, mat_transform = geometry.apply_transformation(me, is_import=False)
        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh apply_transformation")

        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh export")

        fileExt = '.bmp'
        
        # write GoB ZScript variables
        variablesFile = os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZProjects/Default/GoB_variables.zvr")      
        with open(variablesFile, 'wb') as GoBVars:            
            GoBVars.write(pack('<4B', 0xE9, 0x03, 0x00, 0x00))
            #list size
            GoBVars.write(pack('<1B', 0x07))   #NOTE: n list items, update this when adding new items to list
            GoBVars.write(pack('<2B', 0x00, 0x00)) 
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write list size")

            # 0: fileExtension
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.GoZ')
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write fileExtension")

            # 1: textureFormat   
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.bmp') 
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write textureFormat")

            # 2: diffTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S            
            name = utils.prefs().import_diffuse_suffix
            GoBVars.write(name.encode('utf-8'))  
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write diffTexture suffix") 

            # 3: normTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().import_normal_suffix
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write normTexture suffix") 

            # 4: dispTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().import_displace_suffix
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write dispTexture suffix")

            #5: GoB version  
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S 
            GoBVars.write(utils.gob_version().encode('utf-8'))
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write GoB version")

            # 6: Project Path
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().project_path
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "    variablesFile: Write Project Path")
            #end  
            GoBVars.write(pack('<B', 0x00))  #. 
        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "variablesFile: Write GoB_variables")


        with open(os.path.join(pathImport + '/{0}.GoZ'.format(obj.name)), 'wb') as goz_file:            
            numFaces = len(me.polygons)
            numVertices = len(me.vertices)

            # --File Header--
            goz_file.write(b"GoZb 1.0 ZBrush GoZ Binary")
            goz_file.write(pack('<6B', 0x2E, 0x2E, 0x2E, 0x2E, 0x2E, 0x2E))
            goz_file.write(pack('<I', 1))  # obj tag
            goz_file.write(pack('<I', len(obj.name)+24))
            goz_file.write(pack('<Q', 1))
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write File Header")

            # --Object Name--
            goz_file.write(b'GoZMesh_' + obj.name.encode('utf-8'))
            goz_file.write(pack('<4B', 0x89, 0x13, 0x00, 0x00))
            goz_file.write(pack('<I', 20))
            goz_file.write(pack('<Q', 1))
            goz_file.write(pack('<I', 0))           
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write Object Name")            

            # --Vertices--
            goz_file.write(pack('<4B', 0x11, 0x27, 0x00, 0x00))
            goz_file.write(pack('<I', numVertices*3*4+16))
            goz_file.write(pack('<Q', numVertices))            
            for vert in me.vertices:
                modif_coo = obj.matrix_world @ vert.co      # @ is used for matrix multiplications
                modif_coo = mat_transform @ modif_coo
                goz_file.write(pack('<3f', modif_coo[0], modif_coo[1], modif_coo[2]))                
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write Vertices")            

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
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write Faces")

            # --UVs--
            if me.uv_layers.active:
                uv_layer = me.uv_layers[0]
                goz_file.write(pack('<4B', 0xA9, 0x61, 0x00, 0x00))
                goz_file.write(pack('<I', len(me.polygons)*4*2*4+16))
                goz_file.write(pack('<Q', len(me.polygons)))
                
                if utils.prefs().performance_profiling: 
                    start_time = output.profiler(start_time, "    UV: polygones")
                    
                for face in me.polygons:
                    for i, loop_index in enumerate(face.loop_indices):
                        goz_file.write(pack('<2f', uv_layer.data[loop_index].uv.x, 1.0 - uv_layer.data[loop_index].uv.y))
                    if i == 2:
                        goz_file.write(pack('<2f', 0.0, 1.0))
                        
                if utils.prefs().performance_profiling: 
                    start_time = output.profiler(start_time, "    UV: write uvs")
                        
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write UV")


            # --Polypaint--
            if bpy.app.version < (3,4,0): 
                if me.vertex_colors.active:
                    vcoldata = me.vertex_colors.active.data # color[loop_id]
                    vcolArray = bytearray([0] * numVertices * 3)
                    #fill vcArray(vert_idx + rgb_offset) = color_xyz
                    for loop in me.loops: #in the end we will fill verts with last vert_loop color
                        vert_idx = loop.vertex_index
                        vcolArray[vert_idx*3] = int(255*vcoldata[loop.index].color[0])
                        vcolArray[vert_idx*3+1] = int(255*vcoldata[loop.index].color[1])
                        vcolArray[vert_idx*3+2] = int(255*vcoldata[loop.index].color[2])
                    
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  loop")
                        
                    goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*4+16))
                    goz_file.write(pack('<I', numVertices))
                    goz_file.write(pack("<f", 0))
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  write numVertices")

                    for i in range(0, len(vcolArray), 3):
                        goz_file.write(pack('<B', vcolArray[i+2]))
                        goz_file.write(pack('<B', vcolArray[i+1]))
                        goz_file.write(pack('<B', vcolArray[i]))
                        goz_file.write(pack('<B', 0))
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint: write color")

                    vcolArray.clear()
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  vcolArray.clear")

            else:
                # get active color attribut from obj (obj.data.color_attributes). 
                # The temp mesh (me.) has no active color (use obj.data. instead of me.!)
                if obj.data.color_attributes.active_color_name and obj.data.color_attributes.active_color_index >= 0: 

                    vcolArray = geometry.get_vertex_colors(obj, numVertices) 
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  vcolArray")

                    goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*4+16))
                    goz_file.write(pack('<I', numVertices))
                    goz_file.write(pack("<f", 0))
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  write numVertices")

                    for i in range(0, len(vcolArray), 3):
                        goz_file.write(pack('<B', vcolArray[i+2]))
                        goz_file.write(pack('<B', vcolArray[i+1]))
                        goz_file.write(pack('<B', vcolArray[i]))
                        goz_file.write(pack('<B', 0))
                        
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint: write color")

                    vcolArray.clear()
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "    Polypaint:  vcolArray.clear")
                    
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "Write Polypaint")

            # --Mask--
            if not utils.prefs().export_clear_mask:
                for vertexGroup in obj.vertex_groups:
                    if vertexGroup.name.lower() in {'mask'}:
                        goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                        goz_file.write(pack('<I', numVertices*2+16))
                        goz_file.write(pack('<Q', numVertices))                        
                        for i in range(numVertices):                                
                            try:
                                goz_file.write(pack('<H', int((1.0 - vertexGroup.weight(i)) * 65535)))
                            except Exception as e:
                                #print("no vertex group: ", e)
                                goz_file.write(pack('<H', 65535))                                
                
            if utils.prefs().performance_profiling: 
                start_time = output.profiler(start_time, "Write Mask")
        
           
            # --Polygroups--     
            if not utils.prefs().export_polygroups == 'NONE':  
                if utils.prefs().debug_output:
                    print("Export Polygroups: ", utils.prefs().export_polygroups)

                #Polygroups from Face Maps
                """ 
                if utils.prefs().export_polygroups == 'FACE_MAPS':
                    if utils.prefs().debug_output:
                        print(obj.face_maps.items)
                    if obj.face_maps.items:                   
                        goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                        goz_file.write(pack('<I', numFaces*2+16))
                        goz_file.write(pack('<Q', numFaces))  
                                                
                        groupColor=[]                        
                        #create a color for each facemap (0xffff)
                        for faceMap in obj.face_maps:
                            if faceMap:
                                color = geom.random_color()
                                groupColor.append(color)
                            else:
                                groupColor.append(65504)

                        if me.face_maps and len(obj.face_maps) > 0: 
                            for index, map in enumerate(me.face_maps[0].data):
                                if map.value < 0: #write default polygroup color
                                    goz_file.write(pack('<H', 65504))                                                                     
                                else:
                                    if utils.prefs().debug_output:
                                        print("face_maps PG color: ", map.value, groupColor[map.value], numFaces)
                                    goz_file.write(pack('<H', groupColor[map.value]))

                        else:   #assign empty when no face maps are found        
                            for face in me.polygons:   
                                if utils.prefs().debug_output:
                                    print("write empty color for PG face", face.index)     
                                goz_file.write(pack('<H', 65504))

                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "Write Polygroup FaceMaps")  
                    #"""
                

                # Polygroups from Vertex Groups
                if utils.prefs().export_polygroups == 'VERTEX_GROUPS':
                    goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                    goz_file.write(pack('<I', numFaces*2+16))
                    goz_file.write(pack('<Q', numFaces)) 

                    groupColor=[]                        
                    #create a color for each facemap (0xffff)
                    for vg in obj.vertex_groups:
                        color = utils.random_color()
                        groupColor.append(color)
                    #add a color for elements that are not part of a vertex group
                    groupColor.append(0)
                    

                    ''' 
                    # create a list of each vertex group assignement so one vertex can be in x amount of groups 
                    # then check for each face to which groups their vertices are MOST assigned to 
                    # and choose that group for the polygroup color if its on all vertices of the face
                    '''                    
                    if len(obj.vertex_groups) > 0:  
                        vgData = []  
                        for face in me.polygons:
                            vgData.append([])
                            for vert in face.vertices:
                                for vg in me.vertices[vert].groups:
                                    if vg.weight >= utils.prefs().export_weight_threshold and obj.vertex_groups[vg.group].name.lower() != 'mask':         
                                        vgData[face.index].append(vg.group)
                            
                            if vgData[face.index]:                            
                                group =  max(vgData[face.index], key = vgData[face.index].count)
                                count = vgData[face.index].count(group)
                                #print(vgData[face.index])
                                #print("face:", face.index, "verts:", len(face.vertices), "elements:", count, 
                                #"\ngroup:", group, "color:", groupColor[group] )                            
                                if len(face.vertices) == count:
                                    #print(face.index, group, groupColor[group], count)
                                    goz_file.write(pack('<H', groupColor[group]))
                                else:
                                    goz_file.write(pack('<H', 65504))
                            else:
                                goz_file.write(pack('<H', 65504))
                                
                        if utils.prefs().performance_profiling: 
                            start_time = output.profiler(start_time, "Write Polygroup Vertex groups")


                # Polygroups from materials
                if utils.prefs().export_polygroups == 'MATERIALS':   
                    #print("material slots: ", len(obj.material_slots))
                    if len(obj.material_slots) > 0:               
                        goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                        goz_file.write(pack('<I', numFaces*2+16))
                        goz_file.write(pack('<Q', numFaces))  
                        
                        groupColor=[]
                        #create a color for each material slot (0xffff)
                        for mat in obj.material_slots:
                            if mat:
                                color = geometry.random_color()
                                groupColor.append(color)
                            else:
                                groupColor.append(65504)

                        for f in me.polygons:  # iterate over faces
                            #print(f.index, f.material_index, groupColor[f.material_index], numFaces, len(me.polygons))
                            goz_file.write(pack('<H', groupColor[f.material_index]))                        
                            
                    if utils.prefs().performance_profiling: 
                        start_time = output.profiler(start_time, "Write Polygroup materials") 
                    

            # Diff, disp_texture and norm_texture maps
            diff_texture = None
            disp_texture = None
            norm_texture = None

            for mat in obj.material_slots:
                if mat.name:
                    material = bpy.data.materials[mat.name]
                    if material.use_nodes:
                        #print("material:", mat.name, "using nodes \n")
                        for node in material.node_tree.nodes:	
                            #print("node: ", node.type)                                
                            if node.type in {'TEX_IMAGE'} and node.image:
                                #print("IMAGES: ", node.image.name, node.image)	
                                if (utils.prefs().import_diffuse_suffix) in node.image.name:                                
                                    diff_texture = node.image
                                if (utils.prefs().import_displace_suffix) in node.image.name:
                                    disp_texture = node.image
                                if (utils.prefs().import_normal_suffix) in node.image.name:
                                    norm_texture = node.image
                            elif node.type in {'GROUP'}:
                                print("group found")
            user_file_fomrat = scn.render.image_settings.file_format
            scn.render.image_settings.file_format = 'BMP'
            #fileExt = ('.' + utils.prefs().texture_format.lower())
            fileExt = '.bmp'

            if diff_texture:
                name = PATH_PROJECT + obj.name + utils.prefs().import_diffuse_suffix + fileExt
                try:
                    diff_texture.save_render(name)
                    print(name)
                except Exception as e:
                    print(e)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xc9, 0xaf, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))                
                if utils.prefs().performance_profiling: 
                    start_time = output.profiler(start_time, "Write diff_texture")

            if disp_texture:
                name = PATH_PROJECT + obj.name + utils.prefs().import_displace_suffix + fileExt
                try:
                    disp_texture.save_render(name)
                    print(name)
                except Exception as e:
                    print(e)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0xd9, 0xd6, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))                
                if utils.prefs().performance_profiling: 
                    start_time = output.profiler(start_time, "Write disp_texture")

            if norm_texture:
                name = PATH_PROJECT + obj.name + utils.prefs().import_normal_suffix + fileExt                
                try:
                    norm_texture.save_render(name)
                    print(name)                
                except Exception as e:
                    print(e)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0x51, 0xc3, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))                
                if utils.prefs().performance_profiling: 
                    start_time = output.profiler(start_time, "Write norm_texture")
            # end
            goz_file.write(pack('16x'))
            
            if utils.prefs().performance_profiling: 
                output.profiler(start_time, "Write Textures")
                print(30*"-")
                output.profiler(start_total_time, "Total Export Time")
                print(30*"=")

        bpy.data.meshes.remove(me)
        #restore user file format
        scn.render.image_settings.file_format = user_file_fomrat
        return

    def execute(self, context): 
        global PATH_GOZ_PIXOLOGIC  
        if utils.prefs().custom_pixologoc_path:
            PATH_GOZ_PIXOLOGIC =  utils.prefs().pixologoc_path  
        PATH_PROJECT = os.path.join(utils.prefs().project_path)
        PATH_OBJLIST = os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_ObjectList.txt")
        #setup GoZ configuration
        #if not os.path.isfile(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Info.txt"):  
        try:    #install in GoZApps if missing     
            source_GoZ_Info = os.path.join(f"{PATH_GOB}/Blender/")
            target_GoZ_Info = os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/")
            print(source_GoZ_Info, target_GoZ_Info)
            shutil.copytree(source_GoZ_Info, target_GoZ_Info, symlinks=True)            
        except FileExistsError: #if blender folder is found update the info file
            source_GoZ_Info = os.path.join(f"{PATH_GOB}/Blender/GoZ_Info.txt")
            target_GoZ_Info = os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Info.txt")
            shutil.copy2(source_GoZ_Info, target_GoZ_Info)  

            #write blender path to GoZ configuration
            #if not os.path.isfile(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Config.txt"): 
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Config.txt"), 'wt') as GoB_Config:
                blender_path = os.path.join(f"{PATH_BLENDER}").replace('\\', '/')
                GoB_Config.write(f'PATH = "{blender_path}"')
            #specify GoZ application
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_Application.txt"), 'wt') as GoZ_Application:
                GoZ_Application.write("Blender")   

        except Exception as e:
            print(e)

        #update project path
        #print("Project file path: ", f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_ProjectPath.txt")
        with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_ProjectPath.txt"), 'wt') as GoZ_Application:
            GoZ_Application.write(PATH_PROJECT) 

        # remove ZTL files since they mess up Zbrush importing subtools
        if utils.prefs().clean_project_path:
            for file_name in os.listdir(PATH_PROJECT):
                #print(file_name)
                if file_name.endswith(('GoZ', '.ztn', '.ZTL')):
                    #print('cleaning file:', file_name)
                    os.remove(PATH_PROJECT + file_name)
        
        """
        # a object can either be imported as tool or as subtool in zbrush
        # the IMPORT_AS_SUBTOOL needs to be changed in ../Pixologic/GoZBrush/GoZ_Config.txt 
        # for zbrush to recognize the import mode   
            GoZ_Config.txt
                PATH = "C:/PROGRAM FILES/PIXOLOGIC/ZBRUSH 2021/ZBrush.exe"
                IMPORT_AS_SUBTOOL = TRUE
                SHOW_HELP_WINDOW = TRUE 
        """         
        import_as_subtool = 'IMPORT_AS_SUBTOOL = TRUE'
        import_as_tool = 'IMPORT_AS_SUBTOOL = FALSE'   
        try:
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_Config.txt")) as r:
                # IMPORT AS SUBTOOL
                r = r.read().replace('\t', ' ') #fix indentations in source data
                if self.as_tool:
                    new_config = r.replace(import_as_subtool, import_as_tool)
                # IMPORT AS TOOL
                else:
                    new_config = r.replace(import_as_tool, import_as_subtool)
            
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_Config.txt"), "w") as w:
                w.write(new_config)
        except Exception as e:
            print(e)         
            #write blender path to GoZ configuration
            #if not os.path.isfile(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Config.txt"): 
            with open(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZApps/Blender/GoZ_Config.txt"), 'wt') as GoB_Config:
                GoB_Config.write(f"PATH = \'{PATH_BLENDER}\'")   

            
        currentContext = 'OBJECT'
        if context.object and context.object.mode != 'OBJECT':            
            currentContext = context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')       
        
        wm = context.window_manager
        wm.progress_begin(0,100)
        step =  100  / len(context.selected_objects)
        surface_types = ['SURFACE', 'CURVE', 'FONT', 'META']
        
        with open(PATH_OBJLIST, 'wt') as GoZ_ObjectList:
            for i, obj in enumerate(context.selected_objects):
                if obj.type in surface_types:

                    """ 
                    # Avoid annoying None checks later on.
                    if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
                        self.report({'INFO'}, "Object can not be converted to mesh")
                        return {'CANCELLED'}
                        
                    depsgraph = context.evaluated_depsgraph_get()
                    # Invoke to_mesh() for original object.
                    mesh_from_orig = obj.to_mesh()
                    self.report({'INFO'}, f"{len(mesh_from_orig.vertices)} in new mesh without modifiers.")

                    # Remove temporary mesh.
                    obj.to_mesh_clear()
                    # Invoke to_mesh() for evaluated object.
                    object_eval = obj.evaluated_get(depsgraph)
                    mesh_from_eval = object_eval.to_mesh()
                    self.report({'INFO'}, f"{len(mesh_from_eval.vertices)} in new mesh with modifiers.")
                    # Remove temporary mesh.
                    object_eval.to_mesh_clear() 
                    #"""

                    depsgraph = context.evaluated_depsgraph_get()
                    obj_to_convert = obj.evaluated_get(depsgraph)
                    #mesh_tmp = obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph) 
                    mesh_tmp = bpy.data.meshes.new_from_object(obj_to_convert)
                    mesh_tmp.transform(obj.matrix_world)
                    obj_tmp = bpy.data.objects.new((obj.name + '_' + obj.type), mesh_tmp)
                    if utils.prefs().export_merge:
                        geometry.mesh_welder(obj_tmp)
                    
                    if len(mesh_tmp.polygons):
                        print("GoB: ", obj_tmp.name, mesh_tmp.name, len(mesh_tmp.polygons), sep=' / ')
                        self.escape_object_name(obj_tmp)
                        self.exportGoZ(PATH_GOZ_PIXOLOGIC, context.scene, obj_tmp, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj_tmp.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj_tmp.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj_tmp.name}\n')                        
                        #cleanup temp mesh
                        bpy.data.meshes.remove(mesh_tmp)

                elif obj.type in {'MESH'}:
                    depsgraph = bpy.context.evaluated_depsgraph_get() 

                    # if one or less objects check amount of faces, 0 faces will crash zbrush
                    if not utils.prefs().export_modifiers == 'IGNORE':
                        object_eval = obj.evaluated_get(depsgraph)
                        numFaces = len(object_eval.data.polygons)                      
                    else: 
                        numFaces = len(obj.data.polygons)

                    if numFaces > 0: 
                        geometry.process_linked_objects(obj) 
                        geometry.remove_internal_faces(obj)
                        self.escape_object_name(obj)
                        self.exportGoZ(PATH_GOZ_PIXOLOGIC, context.scene, obj, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj.name}\n')
                    else:
                        output.ShowReport(self, ["Object: ", obj.name], "GoB: ZBrush can not import objects without faces", 'COLORSET_01_VEC') 
                    
                else:
                    output.ShowReport(self, [obj.type, obj.name], "GoB: unsupported obj.type found:", 'COLORSET_01_VEC') 
                    #print("GoB: unsupported obj.type found:", obj.type, obj.name)

                wm.progress_update(step * i)                
            wm.progress_end()
            
        global cached_last_edition_time
        try:
            cached_last_edition_time = os.path.getmtime(PATH_OBJLIST)
        except Exception as e:
            print(e)

        PATH_SCRIPT = os.path.join(f"{PATH_GOB}/ZScripts/GoB_Import.zsc")

        
        # only run if PATH_OBJLIST file file is not empty, else zbrush errors
        if not paths.is_file_empty(PATH_OBJLIST) and not utils.prefs().debug_dry_export: 
            path_exists = paths.find_zbrush(self, context, isMacOS)
            if not path_exists:
                bpy.ops.gob.search_zbrush('INVOKE_DEFAULT')
            else:
                if isMacOS:   
                    print("OSX Popen: ", utils.prefs().zbrush_exec)
                    Popen(['open', '-a', utils.prefs().zbrush_exec, PATH_SCRIPT])   
                else: #windows   
                    print("Windows Popen: ", utils.prefs().zbrush_exec)
                    Popen([utils.prefs().zbrush_exec, PATH_SCRIPT], shell=True)  
                if context.object: #restore object context
                    bpy.ops.object.mode_set(mode=currentContext) 
        
        return {'FINISHED'}


    def escape_object_name(self, obj):
        """
        Escape object name so it can be used as a valid file name.
        Keep only alphanumeric characters, underscore, dash and dot, and replace other characters with an underscore.
        Multiple consecutive invalid characters will be replaced with just a single underscore character.
        """        
        import re
        suffix_pattern = '\.(.*)'
        found_string = re.search(suffix_pattern, obj.name)   
        new_name = obj.name
        if found_string:
            # suffixes in zbrush longer than 1 symbol after a . (dot) require a specal addition 
            # of symbol+underline to be exported from zbrush, otherwise the whole suffix gets removed.
            # Due to the complicated name that this would create, only the . (dot) for one symbol suffix are kept, 
            # the others are going to be replaced by a _ (underline) resulting from .001 to _001
            if len(found_string.group()) > 2:              
                new_name = re.sub('[^\w\_\-]+', '_', obj.name)
            else:
                return       
        
        if new_name == obj.name:
            return            
        i = 0
        while new_name in bpy.data.objects.keys(): #while name collision with other scene objs,
            name_cut = None if i == 0 else -2  #in first loop, do not slice name.
            new_name = new_name[:name_cut] + str(i).zfill(2) #add two latters to end of obj name.
            i += 1          
        obj.name = new_name

       
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


class GoB_OT_GoZ_Installer(Operator):
    ''' Run the Pixologic GoZ installer 
        /Troubleshoot Help/GoZ_for_ZBrush_Installer'''
    bl_idname = "gob.install_goz" 
    bl_label = "Run GoZ Installer"

    def execute(self, context):
        """Install GoZ for Windows""" 
        path_exists = paths.find_zbrush(self, context, isMacOS)
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
        font_size_correction = bpy.context.preferences.ui_styles[0].widget_label.points / 10
        return wm.invoke_props_dialog(self, width = int(200 * font_size_correction))

    def execute(self, context):
        self.open_addon_prefs(context)
        return {'FINISHED'}



def run_import_periodically():
    # print("Runing timers update check")
    global cached_last_edition_time, run_background_update

    try:
        file_edition_time = os.path.getmtime(os.path.join(f"{PATH_GOZ_PIXOLOGIC}/GoZBrush/GoZ_ObjectList.txt"))
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



