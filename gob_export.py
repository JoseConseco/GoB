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
import numpy as np
import time
import shutil
from struct import pack
from subprocess import Popen
from bpy.types import Operator
from bpy.props import BoolProperty
from . import paths, utils, geometry, ui, gob_import


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
        PATH_PROJECT = utils.prefs().project_path
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
            # list size
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

            # 5: GoB version
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
            # end
            GoBVars.write(pack('<B', 0x00))  #.
        if utils.prefs().performance_profiling:
            start_time = utils.profiler(start_time, "variablesFile: Write GoB_variables")

        try:
            object_name_bytes = obj.name.encode('ascii')
        except UnicodeEncodeError:
            self.escape_object_name(obj)
            object_name_bytes = obj.name.encode('ascii')

        with open(os.path.join(path_export + '/{0}.GoZ'.format(obj.name)), 'wb') as goz_file:
            numFaces = len(mesh_tmp.polygons)
            numVertices = len(mesh_tmp.vertices)

            # --File Header--
            goz_file.write(b"GoZb 1.0 ZBrush GoZ Binary")
            goz_file.write(pack('<6B', 0x2E, 0x2E, 0x2E, 0x2E, 0x2E, 0x2E))
            goz_file.write(pack('<I', 1))  # obj tag
            goz_file.write(pack('<I', len(object_name_bytes)+24))
            goz_file.write(pack('<Q', 1))
            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Write File Header")

            # --Object Name--
            goz_file.write(b'GoZMesh_' + object_name_bytes)
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

            vertex_coords = np.zeros(numVertices * 3, dtype=np.float32)
            mesh_tmp.vertices.foreach_get('co', vertex_coords)
            vertex_coords = vertex_coords.reshape(-1, 3)

            matrix_world_np = np.array(obj.matrix_world, dtype=np.float32)
            mat_transform_np = np.array(mat_transform, dtype=np.float32)

            homogeneous_coords = np.column_stack([vertex_coords, np.ones(numVertices)])

            # matrix_world
            transformed_coords = (matrix_world_np @ homogeneous_coords.T).T[:, :3]

            # mat_transform
            homogeneous_transformed = np.column_stack([transformed_coords, np.ones(numVertices)])
            final_coords = (mat_transform_np @ homogeneous_transformed.T).T[:, :3]

            goz_file.write(pack(f'<{numVertices * 3}f', *final_coords.flatten()))

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Write Vertices")

            # --Faces--
            goz_file.write(pack('<4B', 0x21, 0x4E, 0x00, 0x00))
            goz_file.write(pack('<I', numFaces*4*4+16))
            goz_file.write(pack('<Q', numFaces))

            face_data = bytearray()

            for face in mesh_tmp.polygons:
                if len(face.vertices) == 4:
                    face_data.extend(pack('<4I', face.vertices[0],
                                face.vertices[1],
                                face.vertices[2],
                                face.vertices[3]))
                elif len(face.vertices) == 3:
                    face_data.extend(pack('<3I4B', face.vertices[0],
                                face.vertices[1],
                                face.vertices[2],
                                0xFF, 0xFF, 0xFF, 0xFF))

            goz_file.write(face_data)

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

                uv_coords = np.zeros(len(uv_layer.data) * 2, dtype=np.float32)

                uv_layer.data.foreach_get('uv', uv_coords)
                uv_coords = uv_coords.reshape(-1, 2)
                if utils.prefs().export_uv_flip_x:
                    uv_coords[:, 0] = 1.0 - uv_coords[:, 0]
                if utils.prefs().export_uv_flip_y:
                    uv_coords[:, 1] = 1.0 - uv_coords[:, 1]

                uv_data = []
                for face in mesh_tmp.polygons:
                    for loop_index in face.loop_indices:
                        x, y = uv_coords[loop_index]
                        uv_data.extend([x, y])

                    if len(face.loop_indices) == 3:
                        uv_data.extend([0.0, 1.0])

                goz_file.write(pack(f'<{len(uv_data)}f', *uv_data))

                if utils.prefs().performance_profiling:
                    start_time = utils.profiler(start_time, "    UV: write uvs")

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Write UV")

            # --Polypaint--
            if bpy.app.version < (3,4,0):
                if mesh_tmp.vertex_colors.active:
                    vcoldata = mesh_tmp.vertex_colors.active.data # color[loop_id]
                    vcolArray = bytearray([0] * numVertices * 3)
                    # fill vcArray(vert_idx + rgb_offset) = color_xyz
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

            elif obj.data.color_attributes.active_color_name and obj.data.color_attributes.active_color_index >= 0:

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
            if utils.prefs().export_mask !='NONE':
                # since blender 4.1, Sculpt mask values are stored in a generic attribute
                # https://developer.blender.org/docs/release_notes/4.1/python_api/#mesh
                if '.sculpt_mask' in mesh_tmp.attributes and utils.prefs().export_mask == 'SCULPT_MASK' and bpy.app.version >= (4, 1, 0):
                    goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                    goz_file.write(pack('<I', numVertices*2+16))
                    goz_file.write(pack('<Q', numVertices))

                    mask_data = np.zeros(numVertices, dtype=np.float32)
                    mask_attr = mesh_tmp.attributes.get(".sculpt_mask")

                    if mask_attr and len(mask_attr.data) == len(mask_data):
                        mask_attr.data.foreach_get('value', mask_data)
                    else:
                        mask_data[:] = [0.0] * len(mask_data)

                    mask_data = np.where(mask_data < 0, 0.0, mask_data)
                    mask_values = ((1.0 - mask_data) * 65535).astype(np.uint16)

                    goz_file.write(pack(f'<{numVertices}H', *mask_values))

                else:
                    for vertexGroup in obj.vertex_groups:
                        if vertexGroup.name.lower() in {'mask'}:
                            goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                            goz_file.write(pack('<I', numVertices*2+16))
                            goz_file.write(pack('<Q', numVertices))
                            for i in range(numVertices):
                                try:
                                    goz_file.write(pack('<H', int((1.0 - vertexGroup.weight(i)) * 65535)))
                                except Exception as e:
                                    # print("no vertex group: ", e)
                                    goz_file.write(pack('<H', 65535))

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Write Mask")

            # --Polygroups--
            if utils.prefs().export_polygroups != 'NONE':
                if utils.prefs().debug_output:
                    print("Export Polygroups: ", utils.prefs().export_polygroups)

                # Polygroups from Face Sets
                if utils.prefs().export_polygroups == 'FACE_SETS':

                    goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                    goz_file.write(pack('<I', numFaces*2+16))
                    goz_file.write(pack('<Q', numFaces))

                    face_attr = geometry.get_sculpt_face_set_attribute(mesh_tmp)
                    if utils.prefs().debug_output:
                        print("Exporting Face Sets: ", face_attr)

                    if face_attr is not None and len(face_attr.data) == numFaces:
                        face_set_data = np.zeros(numFaces, dtype=np.int32)
                        face_attr.data.foreach_get("value", face_set_data)

                        face_set_data = np.where(face_set_data < 0, 65504, face_set_data)
                        face_set_data = face_set_data.astype(np.uint16)
                        goz_file.write(pack(f'<{numFaces}H', *face_set_data))

                        if utils.prefs().debug_output:
                            print(f"Face sets exported: {numFaces} faces")
                            unique_values = np.unique(face_set_data)
                            print(f"Unique face set values: {unique_values}")

                    else:   #assign empty when no face sets are found
                        default_face_set_data = np.full(numFaces, 65504, dtype=np.uint16)
                        goz_file.write(pack(f'<{numFaces}H', *default_face_set_data))

                        if utils.prefs().debug_output:
                            print(f"Default face sets written: {numFaces} faces")

                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(start_time, "Write Polygroup FaceSets")

                # Polygroups from Vertex Groups
                if utils.prefs().export_polygroups == 'VERTEX_GROUPS':
                    goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                    goz_file.write(pack('<I', numFaces*2+16))
                    goz_file.write(pack('<Q', numFaces))

                    groupColor=[]
                    # create a color for each facemap (0xffff)
                    for vg in obj.vertex_groups:
                        color = utils.random_color()
                        groupColor.append(color)
                    # add a color for elements that are not part of a vertex group
                    groupColor.append(0)

                    if len(obj.vertex_groups) > 0:
                        vgData = []
                        for face in mesh_tmp.polygons:
                            vgData.append([])
                            for vert in face.vertices:
                                for vg in mesh_tmp.vertices[vert].groups:
                                    if vg.weight >= utils.prefs().export_weight_threshold and vg.group < len(obj.vertex_groups) and obj.vertex_groups[vg.group].name.lower() != 'mask':
                                        vgData[face.index].append(vg.group)

                            if vgData[face.index]:
                                group =  max(vgData[face.index], key = vgData[face.index].count)
                                count = vgData[face.index].count(group)
                                if len(face.vertices) == count:
                                    goz_file.write(pack('<H', groupColor[group]))
                                else:
                                    goz_file.write(pack('<H', 65504))
                            else:
                                goz_file.write(pack('<H', 65504))

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(start_time, "Write Polygroup Vertex groups")

                # Polygroups from materials
                if utils.prefs().export_polygroups == 'MATERIALS':
                    if len(obj.material_slots) > 0:
                        goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
                        goz_file.write(pack('<I', numFaces*2+16))
                        goz_file.write(pack('<Q', numFaces))

                        groupColor=[]
                        for mat in obj.material_slots:
                            if mat:
                                color = utils.random_color()
                                groupColor.append(color)
                            else:
                                groupColor.append(65504)

                        for f in mesh_tmp.polygons:
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
                        for node in material.node_tree.nodes:
                            if node.type in {'TEX_IMAGE'} and node.image:
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
        # restore user file format
        scn.render.image_settings.file_format = user_file_fomrat
        return

    def execute(self, context):

        if utils.prefs().custom_pixologoc_path:
            paths.PATH_GOZ =  utils.prefs().pixologoc_path

        PATH_PROJECT = utils.prefs().project_path

        try:
            source_GoZ_Info = os.path.join(paths.PATH_GOB, "Blender")
            target_GoZ_Info = os.path.join(paths.PATH_GOZ, "GoZApps", "Blender")
            print(source_GoZ_Info, target_GoZ_Info)
            shutil.copytree(source_GoZ_Info, target_GoZ_Info, symlinks=True)
        except FileExistsError:
            source_GoZ_Info = os.path.join(paths.PATH_GOB, "Blender", "GoZ_Info.txt")
            target_GoZ_Info = os.path.join(paths.PATH_GOZ, "GoZApps", "Blender", "GoZ_Info.txt")
            shutil.copy2(source_GoZ_Info, target_GoZ_Info)

            with open(os.path.join(paths.PATH_GOZ, "GoZApps", "Blender", "GoZ_Config.txt"), 'wt') as GoB_Config:
                blender_path = os.path.join(paths.PATH_BLENDER).replace('\\', '/')
                GoB_Config.write(f'PATH = "{blender_path}"')
            with open(os.path.join(paths.PATH_GOZ, "GoZBrush", "GoZ_Application.txt"), 'wt') as GoZ_Application:
                GoZ_Application.write("Blender")

        except Exception as e:
            print(e)

        with open(os.path.join(paths.PATH_GOZ, "GoZBrush", "GoZ_ProjectPath.txt"), 'wt') as GoZ_Application:
            GoZ_Application.write(PATH_PROJECT)

        if utils.prefs().clean_project_path:
            for file_name in os.listdir(PATH_PROJECT):
                if file_name.lower().endswith(('.goz', '.ztn', '.ztl')):
                    print('cleaning file:', file_name)
                    os.remove(os.path.join(PATH_PROJECT, file_name))

        import_as_subtool = 'IMPORT_AS_SUBTOOL = TRUE'
        import_as_tool = 'IMPORT_AS_SUBTOOL = FALSE'

        try:
            with open(paths.PATH_CONFIG) as r:
                r = r.read().replace('\t', ' ')
                if self.as_tool:
                    new_config = r.replace(import_as_subtool, import_as_tool)
                else:
                    new_config = r.replace(import_as_tool, import_as_subtool)

            with open(paths.PATH_CONFIG, "w") as w:
                w.write(new_config)

        except Exception as e:
            print("Goz config missing, writing file ", e)
            with open(os.path.join(paths.PATH_GOZ, "GoZApps", "Blender", "GoZ_Config.txt"), 'wt') as GoB_Config:
                GoB_Config.write(f"PATH = \'{paths.PATH_BLENDER}\'")

        currentContext = None
        if context.object:
            currentContext = context.object.mode
            if context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

        wm = context.window_manager
        wm.progress_begin(0,100)
        step =  100  / len(context.selected_objects)
        surface_types = ['SURFACE', 'CURVE', 'FONT', 'META']

        with open(paths.PATH_OBJLIST, 'wt') as GoZ_ObjectList:
            for i, obj in enumerate(context.selected_objects):
                if obj.type in surface_types:

                    depsgraph = context.evaluated_depsgraph_get()
                    obj_to_convert = obj.evaluated_get(depsgraph)
                    mesh_tmp = bpy.data.meshes.new_from_object(obj_to_convert)
                    mesh_tmp.transform(obj.matrix_world)
                    obj_tmp = bpy.data.objects.new(f'{obj.name}_{obj.type}', mesh_tmp)

                    if utils.prefs().export_merge:
                        geometry.mesh_welder(obj_tmp)

                    if len(mesh_tmp.polygons):
                        print("GoB: ", obj_tmp.name, mesh_tmp.name, len(mesh_tmp.polygons), sep=' / ')
                        self.escape_object_name(obj_tmp)
                        self.exportGoZ(context.scene, obj_tmp, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj_tmp.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj_tmp.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj_tmp.name}\n')
                        bpy.data.meshes.remove(mesh_tmp)

                elif obj.type in {'MESH'}:
                    depsgraph = bpy.context.evaluated_depsgraph_get()

                    if utils.prefs().export_modifiers != 'IGNORE':
                        object_eval = obj.evaluated_get(depsgraph)
                        numFaces = len(object_eval.data.polygons)
                    else:
                        numFaces = len(obj.data.polygons)

                    if numFaces > 0:
                        geometry.process_linked_objects(obj)
                        geometry.remove_internal_faces(obj)

                        if bpy.ops.geometry.color_attribute_convert.poll():
                            bpy.ops.geometry.color_attribute_convert(domain='POINT', data_type='FLOAT_COLOR')
                            obj.data.update()

                        self.escape_object_name(obj)
                        self.exportGoZ(context.scene, obj, f'{PATH_PROJECT}')
                        with open( f"{PATH_PROJECT}{obj.name}.ztn", 'wt') as ztn:
                            ztn.write(f'{PATH_PROJECT}{obj.name}')
                        GoZ_ObjectList.write(f'{PATH_PROJECT}{obj.name}\n')
                    else:
                        ui.ShowReport(self, ["Object: ", obj.name], "GoB: ZBrush can not import objects without faces", 'COLORSET_01_VEC')

                else:
                    ui.ShowReport(self, [obj.type, obj.name], "GoB: unsupported obj.type found:", 'COLORSET_01_VEC')

                wm.progress_update(step * i)
            wm.progress_end()

        try:
            gob_import.cached_last_edition_time = os.path.getmtime(paths.PATH_OBJLIST)
        except Exception as e:
            print(e)

        if not paths.is_file_empty(paths.PATH_OBJLIST):
            path_exists = paths.find_zbrush(self, context, paths.isMacOS)
            if utils.prefs().export_run_zbrush:
                if not path_exists:
                    bpy.ops.gob.search_zbrush('INVOKE_DEFAULT')
                else:
                    if paths.isMacOS:
                        print("OSX Popen: ", utils.prefs().zbrush_exec)
                        Popen(['open', '-a', utils.prefs().zbrush_exec, paths.PATH_SCRIPT])
                    else:
                        print("Windows Popen: ", utils.prefs().zbrush_exec)
                        Popen([utils.prefs().zbrush_exec, paths.PATH_SCRIPT], shell=True)

        if context.object and currentContext:
            bpy.ops.object.mode_set(mode=currentContext)

        return {'FINISHED'}

    def escape_object_name(self, obj):
        import re

        original_name = obj.name
        new_name = re.sub(r'[^A-Za-z0-9_-]+', '_', original_name)
        new_name = re.sub(r'_+', '_', new_name).strip('_-')

        if not new_name:
            new_name = "Object"

        if new_name == original_name:
            return

        base_name = new_name
        i = 0
        while new_name in bpy.data.objects and bpy.data.objects[new_name] != obj:
            new_name = f"{base_name}_{i:02d}"
            i += 1
        obj.name = new_name
