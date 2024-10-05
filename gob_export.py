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
import time
import shutil
from struct import pack
from subprocess import Popen
from bpy.types import Operator
from bpy.props import BoolProperty
from . import paths, utils, geometry, ui


class GoB_OT_export(Operator):
    bl_idname = "scene.gob_export"
    bl_label = "Export to ZBrush"
    bl_description = "Export selected Objects to ZBrush"

    as_tool: BoolProperty(
        name="Export As Tool",
        description="Export as a tool instead of a subtool",
        default=False,
    )
    
    @classmethod
    def poll(cls, context):              
        return geometry.export_poll(cls, context)    

    def exportGoZ(self, scn, obj, path_export):      
        PATH_PROJECT = os.path.join(utils.prefs().project_path).replace("\\", "/")
        if utils.prefs().performance_profiling: 
            print("\n", 100*"=")
            start_time = utils.profiler(time.perf_counter(), "Export Profiling: " + obj.name)
            start_total_time = utils.profiler(time.perf_counter(), 80*"=")

        mesh_tmp = geometry.apply_modifiers(obj)
        if utils.prefs().performance_profiling: 
            start_time = utils.profiler(start_time, "Make Mesh apply_modifiers")

        mesh_tmp.calc_loop_triangles()
        if utils.prefs().performance_profiling: 
            start_time = utils.profiler(start_time, "Make Mesh calc_loop_triangles")

        mesh_tmp, mat_transform = geometry.apply_transformation(mesh_tmp, is_import=False)
        if utils.prefs().performance_profiling: 
            start_time = utils.profiler(start_time, "Make Mesh apply_transformation")

        if utils.prefs().performance_profiling: 
            start_time = utils.profiler(start_time, "Make Mesh export")

        fileExt = '.bmp'
        
        # write GoB ZScript variables   
        with open(paths.PATH_VARS , 'wb') as GoBVars:            
            GoBVars.write(pack('<4B', 0xE9, 0x03, 0x00, 0x00))
            #list size
            GoBVars.write(pack('<1B', 0x07))   #NOTE: n list items, update this when adding new items to list
            GoBVars.write(pack('<2B', 0x00, 0x00)) 
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write list size")

            # 0: fileExtension
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.GoZ')
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write fileExtension")

            # 1: textureFormat   
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            GoBVars.write(b'.bmp') 
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write textureFormat")

            # 2: diffTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S            
            name = utils.prefs().import_diffuse_suffix
            GoBVars.write(name.encode('utf-8'))  
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write diffTexture suffix") 

            # 3: normTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().import_normal_suffix
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write normTexture suffix") 

            # 4: dispTexture suffix
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().import_displace_suffix
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write dispTexture suffix")

            #5: GoB version  
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S 
            GoBVars.write(utils.gob_version().encode('utf-8'))
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write GoB version")

            # 6: Project Path
            GoBVars.write(pack('<2B',0x00, 0x53))   #.S
            name = utils.prefs().project_path
            GoBVars.write(name.encode('utf-8')) 
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "    variablesFile: Write Project Path")
            #end  
            GoBVars.write(pack('<B', 0x00))  #. 
        if utils.prefs().performance_profiling: 
            start_time = utils.profiler(start_time, "variablesFile: Write GoB_variables")


        with open(os.path.join(path_export + '/{0}.GoZ'.format(obj.name)), 'wb') as goz_file:            
            numFaces = len(mesh_tmp.polygons)
            numVertices = len(mesh_tmp.vertices)

            # --File Header--
            goz_file.write(b"GoZb 1.0 ZBrush GoZ Binary")
            goz_file.write(pack('<6B', 0x2E, 0x2E, 0x2E, 0x2E, 0x2E, 0x2E))
            goz_file.write(pack('<I', 1))  # obj tag
            goz_file.write(pack('<I', len(obj.name)+24))
            goz_file.write(pack('<Q', 1))
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "Write File Header")

            # --Object Name--
            goz_file.write(b'GoZMesh_' + obj.name.encode('utf-8'))
            goz_file.write(pack('<4B', 0x89, 0x13, 0x00, 0x00))
            goz_file.write(pack('<I', 20))
            goz_file.write(pack('<Q', 1))
            goz_file.write(pack('<I', 0))           
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "Write Object Name")            

            # --Vertices--
            goz_file.write(pack('<4B', 0x11, 0x27, 0x00, 0x00))
            goz_file.write(pack('<I', numVertices*3*4+16))
            goz_file.write(pack('<Q', numVertices))            
            for vert in mesh_tmp.vertices:
                modif_coo = obj.matrix_world @ vert.co      # @ is used for matrix multiplications
                modif_coo = mat_transform @ modif_coo
                goz_file.write(pack('<3f', modif_coo[0], modif_coo[1], modif_coo[2]))                
            
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "Write Vertices")            

            # --Faces--
            goz_file.write(pack('<4B', 0x21, 0x4E, 0x00, 0x00))
            goz_file.write(pack('<I', numFaces*4*4+16))
            goz_file.write(pack('<Q', numFaces))
            for face in mesh_tmp.polygons:
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
                start_time = utils.profiler(start_time, "Write Faces")

            # --UVs--
            if mesh_tmp.uv_layers.active:
                uv_layer = mesh_tmp.uv_layers[0]
                goz_file.write(pack('<4B', 0xA9, 0x61, 0x00, 0x00))
                goz_file.write(pack('<I', len(mesh_tmp.polygons)*4*2*4+16))
                goz_file.write(pack('<Q', len(mesh_tmp.polygons)))
                
                if utils.prefs().performance_profiling: 
                    start_time = utils.profiler(start_time, "    UV: polygones")
               
                for face in mesh_tmp.polygons:
                    for loop_index in face.loop_indices:
                        uv = uv_layer.data[loop_index].uv
                        if utils.prefs().export_uv_flip_x:
                            uv.x = 1.0 - uv.x
                        if utils.prefs().export_uv_flip_y:
                            uv.y = 1.0 - uv.y

                        goz_file.write(pack('<2f', uv.x, uv.y))

                    if len(face.loop_indices) == 3:
                        goz_file.write(pack('<2f', 0.0, 1.0))
                        
                if utils.prefs().performance_profiling: 
                    start_time = utils.profiler(start_time, "    UV: write uvs")
                        
            if utils.prefs().performance_profiling: 
                start_time = utils.profiler(start_time, "Write UV")


            # --Polypaint--
            if bpy.app.version < (3,4,0): 
                if mesh_tmp.vertex_colors.active:
                    vcoldata = mesh_tmp.vertex_colors.active.data # color[loop_id]
                    vcolArray = bytearray([0] * numVertices * 3)
                    #fill vcArray(vert_idx + rgb_offset) = color_xyz
                    for loop in mesh_tmp.loops: #in the end we will fill verts with last vert_loop color
                        vert_idx = loop.vertex_index
                        vcolArray[vert_idx*3] = int(255*vcoldata[loop.index].color[0])
                        vcolArray[vert_idx*3+1] = int(255*vcoldata[loop.index].color[1])
                        vcolArray[vert_idx*3+2] = int(255*vcoldata[loop.index].color[2])
                    
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  loop")
                        
                    goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*4+16))
                    goz_file.write(pack('<I', numVertices))
                    goz_file.write(pack("<f", 0))
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  write numVertices")

                    for i in range(0, len(vcolArray), 3):
                        goz_file.write(pack('<B', vcolArray[i+2]))
                        goz_file.write(pack('<B', vcolArray[i+1]))
                        goz_file.write(pack('<B', vcolArray[i]))
                        goz_file.write(pack('<B', 0))
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint: write color")

                    vcolArray.clear()
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  vcolArray.clear")

            else:
                # get active color attribut from obj (obj.data.color_attributes). 
                # The temp mesh (mesh_tmp.) has no active color (use obj.data. instead of mesh_tmp.!)
                if obj.data.color_attributes.active_color_name and obj.data.color_attributes.active_color_index >= 0: 

                    vcolArray = geometry.get_vertex_colors(mesh_tmp, obj, numVertices) 
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  vcolArray")

                    goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*4+16))
                    goz_file.write(pack('<I', numVertices))
                    goz_file.write(pack("<f", 0))
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  write numVertices")

                    vcol_data = bytearray()
                    for i in range(0, len(vcolArray), 3):
                        vcol_data.extend(pack('<4B', vcolArray[i+2], vcolArray[i+1], vcolArray[i], 0))

                    goz_file.write(vcol_data)
                        
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint: write color")

                    vcolArray.clear()
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "    Polypaint:  vcolArray.clear")
                    
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "Write Polypaint")

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
                start_time = utils.profiler(start_time, "Write Mask")
        
           
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

                        if mesh_tmp.face_maps and len(obj.face_maps) > 0: 
                            for index, map in enumerate(mesh_tmp.face_maps[0].data):
                                if map.value < 0: #write default polygroup color
                                    goz_file.write(pack('<H', 65504))                                                                     
                                else:
                                    if utils.prefs().debug_output:
                                        print("face_maps PG color: ", map.value, groupColor[map.value], numFaces)
                                    goz_file.write(pack('<H', groupColor[map.value]))

                        else:   #assign empty when no face maps are found        
                            for face in mesh_tmp.polygons:   
                                if utils.prefs().debug_output:
                                    print("write empty color for PG face", face.index)     
                                goz_file.write(pack('<H', 65504))

                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "Write Polygroup FaceMaps")  
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
                        for face in mesh_tmp.polygons:
                            vgData.append([])
                            for vert in face.vertices:
                                for vg in mesh_tmp.vertices[vert].groups:
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
                            start_time = utils.profiler(start_time, "Write Polygroup Vertex groups")


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
                                color = utils.random_color()
                                groupColor.append(color)
                            else:
                                groupColor.append(65504)

                        for f in mesh_tmp.polygons:  # iterate over faces
                            #print(f.index, f.material_index, groupColor[f.material_index], numFaces, len(mesh_tmp.polygons))
                            goz_file.write(pack('<H', groupColor[f.material_index]))                        
                            
                    if utils.prefs().performance_profiling: 
                        start_time = utils.profiler(start_time, "Write Polygroup materials") 
                    

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
                    start_time = utils.profiler(start_time, "Write diff_texture")

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
                    start_time = utils.profiler(start_time, "Write disp_texture")

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
                    start_time = utils.profiler(start_time, "Write norm_texture")
            # end
            goz_file.write(pack('16x'))
            
            if utils.prefs().performance_profiling: 
                utils.profiler(start_time, "Write Textures")
                print(30*"-")
                utils.profiler(start_total_time, "Total Export Time")
                print(30*"=")

        bpy.data.meshes.remove(mesh_tmp)
        #restore user file format
        scn.render.image_settings.file_format = user_file_fomrat
        return

    def execute(self, context): 
       
        if utils.prefs().custom_pixologoc_path:
            paths.PATH_GOZ =  utils.prefs().pixologoc_path  
        PATH_PROJECT = os.path.join(utils.prefs().project_path)
        
        #setup GoZ configuration
        #if not os.path.isfile(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Info.txt"):  
        try:    #install in GoZApps if missing     
            source_GoZ_Info = os.path.join(f"{paths.PATH_GOB}/Blender/")
            target_GoZ_Info = os.path.join(f"{paths.PATH_GOZ}/GoZApps/Blender/")
            print(source_GoZ_Info, target_GoZ_Info)
            shutil.copytree(source_GoZ_Info, target_GoZ_Info, symlinks=True)            
        except FileExistsError: #if blender folder is found update the info file
            source_GoZ_Info = os.path.join(f"{paths.PATH_GOB}/Blender/GoZ_Info.txt")
            target_GoZ_Info = os.path.join(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Info.txt")
            shutil.copy2(source_GoZ_Info, target_GoZ_Info)  

            #write blender path to GoZ configuration
            #if not os.path.isfile(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt"): 
            with open(os.path.join(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt"), 'wt') as GoB_Config:
                blender_path = os.path.join(f"{paths.PATH_BLENDER}").replace('\\', '/')
                GoB_Config.write(f'PATH = "{blender_path}"')
            #specify GoZ application
            with open(os.path.join(f"{paths.PATH_GOZ}/GoZBrush/GoZ_Application.txt"), 'wt') as GoZ_Application:
                GoZ_Application.write("Blender")   

        except Exception as e:
            print(e)

        #update project path
        #print("Project file path: ", f"{paths.PATH_GOZ}/GoZBrush/GoZ_ProjectPath.txt")
        with open(os.path.join(f"{paths.PATH_GOZ}/GoZBrush/GoZ_ProjectPath.txt"), 'wt') as GoZ_Application:
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
            with open(paths.PATH_CONFIG) as r:
                # IMPORT AS SUBTOOL
                r = r.read().replace('\t', ' ') #fix indentations in source data
                if self.as_tool:
                    new_config = r.replace(import_as_subtool, import_as_tool)
                # IMPORT AS TOOL
                else:
                    new_config = r.replace(import_as_tool, import_as_subtool)
            
            with open(paths.PATH_CONFIG, "w") as w:
                w.write(new_config)

        except Exception as e:
            print("Goz config missing, writing file ", e)         
            #write blender path to GoZ configuration
            #if not os.path.isfile(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt"): 
            with open(os.path.join(f"{paths.PATH_GOZ}/GoZApps/Blender/GoZ_Config.txt"), 'wt') as GoB_Config:
                GoB_Config.write(f"PATH = \'{paths.PATH_BLENDER}\'")   

            
        currentContext = 'OBJECT'
        if context.object and context.object.mode != 'OBJECT':            
            currentContext = context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')       
        
        wm = context.window_manager
        wm.progress_begin(0,100)
        step =  100  / len(context.selected_objects)
        surface_types = ['SURFACE', 'CURVE', 'FONT', 'META']
        
        with open(paths.PATH_OBJLIST, 'wt') as GoZ_ObjectList:
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
                        self.exportGoZ(context.scene, obj_tmp, f'{PATH_PROJECT}')
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
                        self.exportGoZ(context.scene, obj, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj.name}\n')
                    else:
                        ui.ShowReport(self, ["Object: ", obj.name], "GoB: ZBrush can not import objects without faces", 'COLORSET_01_VEC') 
                    
                else:
                    ui.ShowReport(self, [obj.type, obj.name], "GoB: unsupported obj.type found:", 'COLORSET_01_VEC') 
                    #print("GoB: unsupported obj.type found:", obj.type, obj.name)

                wm.progress_update(step * i)                
            wm.progress_end()
            
        global cached_last_edition_time
        try:
            cached_last_edition_time = os.path.getmtime(paths.PATH_OBJLIST)
        except Exception as e:
            print(e)
        
        # only run if PATH_OBJLIST file file is not empty, else zbrush errors
        if not paths.is_file_empty(paths.PATH_OBJLIST) and not utils.prefs().debug_dry_export: 
            path_exists = paths.find_zbrush(self, context, paths.isMacOS)
            if not path_exists:
                bpy.ops.gob.search_zbrush('INVOKE_DEFAULT')
            else:
                if paths.isMacOS:   
                    print("OSX Popen: ", utils.prefs().zbrush_exec)
                    Popen(['open', '-a', utils.prefs().zbrush_exec, paths.PATH_SCRIPT])   
                else: #windows   
                    print("Windows Popen: ", utils.prefs().zbrush_exec)
                    Popen([utils.prefs().zbrush_exec, paths.PATH_SCRIPT], shell=True)  
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

