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
import time
import os
from struct import pack, unpack
from copy import deepcopy
import string

from . import addon_updater_ops


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
cached_last_edition_time = time.time() - 10.0
preview_collections = {}


def draw_goz(self, context):
    global run_background_update, icons
    icons = preview_collections["main"]

    if context.region.alignment != 'RIGHT':
        layout = self.layout
        row = layout.row(align=True)
        row.operator(operator="scene.gob_export", text="Export", emboss=True, icon_value=icons["GOZ_SEND"].icon_id)
        if run_background_update:
            row.operator(operator="scene.gob_import", text="Import", emboss=True, depress=True, icon_value=icons["GOZ_SYNC_ENABLED"].icon_id)
        else:
            row.operator(operator="scene.gob_import", text="Import", emboss=True, depress=False, icon_value=icons["GOZ_SYNC_DISABLED"].icon_id)


class GoB_OT_import(bpy.types.Operator):
    bl_idname = "scene.gob_import"
    bl_label = "GOZ import"
    bl_description = "GOZ import background listener"

    def GoZit(self, pathFile):
        scn = bpy.context.scene
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences
        diff = False
        disp = False
        nmp = False
        utag = 0
        vertsData = []
        facesData = []
        polypaint = []
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
            me = bpy.data.meshes.new(objName)
            tag = goz_file.read(4)
            while tag:
                print('tags: ', tag)
                if tag == b'\x89\x13\x00\x00':
                    cnt = unpack('<L', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                elif tag == b'\x11\x27\x00\x00':  # Vertices
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        co1 = unpack('<f', goz_file.read(4))[0]
                        co2 = unpack('<f', goz_file.read(4))[0]
                        co3 = unpack('<f', goz_file.read(4))[0]
                        vertsData.append((co1, co2, co3))
                elif tag == b'\x21\x4e\x00\x00':  # Faces
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

                elif tag == b'\xa9\x61\x00\x00':  # UVs
                    break
                elif tag == b'\xb9\x88\x00\x00':  # Polypainting
                    break
                elif tag == b'\x32\x75\x00\x00':  # Mask
                    break
                elif tag == b'\x41\x9c\x00\x00':  # Polyroups
                    break
                elif tag == b'\x00\x00\x00\x00':  # End
                    break
                else:
                    # print(f"unknown tag:{tag}. Skip it...")
                    if utag >= 10:
                        print("...Too many mesh tags unknown...")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                tag = goz_file.read(4)
            me.from_pydata(vertsData, [], facesData)  # Assume mesh data in ready to write to mesh..
            del vertsData
            del facesData
            if pref.flip_y:  # fixes bad mesh orientation for some people
                me.transform(mathutils.Matrix([
                    (-1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., 1., 0., 0.),
                    (0., 0., 0., 1.)]))
            else:
                me.transform(mathutils.Matrix([
                    (1., 0., 0., 0.),
                    (0., 0., 1., 0.),
                    (0., -1., 0., 0.),
                    (0., 0., 0., 1.)]))

            if objName in bpy.data.objects.keys():  # if obj already exist do code below
                obj = bpy.data.objects[objName]
                oldMesh = obj.data
                instances = [ob for ob in bpy.data.objects if ob.data == obj.data]
                for old_mat in oldMesh.materials:
                    me.materials.append(old_mat)
                for instance in instances:
                    instance.data = me
                bpy.data.meshes.remove(oldMesh)
                obj.data.transform(obj.matrix_world.inverted()) #assume we have to rever transformation from obj mode
                obj.select_set(True)
                if len(obj.material_slots) > 0:
                    if obj.material_slots[0].material is not None:
                        objMat = obj.material_slots[0].material
                    else:
                        objMat = bpy.data.materials.new('GoB_{0}'.format(objName))
                        obj.material_slots[0].material = objMat
                else:
                    objMat = bpy.data.materials.new('GoB_{0}'.format(objName))
                    obj.data.materials.append(objMat)
                create_node_material(objMat)
            else:
                obj = bpy.data.objects.new(objName, me)
                objMat = bpy.data.materials.new('GoB_{0}'.format(objName))
                obj.data.materials.append(objMat)
                scn.collection.objects.link(obj)
                create_node_material(objMat)
            utag = 0

            while tag:
                if tag == b'\xa9\x61\x00\x00':  # UVs
                    me.uv_layers.new()
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0] #face count..
                    uv_layer = me.uv_layers[0]
                    for tri in me.polygons:
                        for i, loop_index in enumerate(tri.loop_indices):
                            x, y = unpack('<2f', goz_file.read(8))
                            uv_layer.data[loop_index].uv = x, 1. - y
                        if i < 3:  # cos uv always have 4 coords... ??
                            x, y = unpack('<2f', goz_file.read(8))

                elif tag == b'\xb9\x88\x00\x00':  # Polypainting
                    min = 255
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        data = unpack('<3B', goz_file.read(3))
                        unpack('<B', goz_file.read(1))  # Alpha
                        if data[0] < min:
                            min = data[0]
                        polypaint.append(data)
                    if min < 250:
                        vertexColor = me.vertex_colors.new()
                        iv = 0
                        for poly in me.polygons:
                            for loop_index in poly.loop_indices:
                                loop = me.loops[loop_index]
                                v = loop.vertex_index
                                color = polypaint[v]
                                if bpy.app.version > (2, 79, 0):
                                    vertexColor.data[iv].color = [color[2]/255, color[1]/255, color[0]/255, 1]
                                else:
                                    vertexColor.data[iv].color = [color[2]/255, color[1]/255, color[0]/255]
                                iv += 1
                    del polypaint

                elif tag == b'\x32\x75\x00\x00':  # Mask
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    if 'mask' in obj.vertex_groups:
                        obj.vertex_groups.remove(obj.vertex_groups['mask'])
                    groupMask = obj.vertex_groups.new(name='mask')
                    for i in range(cnt):
                        data = unpack('<H', goz_file.read(2))[0] / 65535.
                        groupMask.add([i], 1.-data, 'ADD')

                elif tag == b'\x41\x9c\x00\x00':  # Polyroups
                    groups = []
                    goz_file.seek(4, 1)
                    cnt = unpack('<Q', goz_file.read(8))[0]
                    for i in range(cnt):
                        gr = unpack('<H', goz_file.read(2))[0]
                        if gr not in groups:
                            if str(gr) in obj.vertex_groups:
                                obj.vertex_groups.remove(obj.vertex_groups[str(gr)])
                            polygroup = obj.vertex_groups.new(name=str(gr))
                            groups.append(gr)
                        else:
                            polygroup = obj.vertex_groups[str(gr)]
                        polygroup.add(list(me.polygons[i].vertices), 1., 'ADD')
                    try:
                        obj.vertex_groups.remove(obj.vertex_groups.get('0'))
                    except:
                        pass
                elif tag == b'\x00\x00\x00\x00':
                    break  # End

                elif tag == b'\xc9\xaf\x00\x00':  # Diff map
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    diffName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(diffName.decode('utf-8'))
                    img = bpy.data.images.load(diffName.strip().decode('utf-8'))
                    diff = True
                    txtDiff = bpy.data.textures.new("GoB_diffuse", 'IMAGE')
                    txtDiff.image = img
                    # me.uv_textures[0].data[0].image = img
                elif tag == b'\xd9\xd6\x00\x00':  # Disp map
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    dispName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(dispName.decode('utf-8'))
                    img = bpy.data.images.load(dispName.strip().decode('utf-8'))
                    disp = True
                    txtDisp = bpy.data.textures.new("GoB_displacement", 'IMAGE')
                    txtDisp.image = img
                elif tag == b'\x51\xc3\x00\x00':  # Normal map
                    cnt = unpack('<I', goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    nmpName = unpack('%ss' % cnt, goz_file.read(cnt))[0]
                    print(nmpName.decode('utf-8'))
                    img = bpy.data.images.load(nmpName.strip().decode('utf-8'))
                    nmp = True
                    txtNmp = bpy.data.textures.new("GoB_normal", 'IMAGE')
                    txtNmp.image = img
                    txtNmp.use_normal_map = True
                else:
                    print("unknown tag:{0}\ntry to skip it...".format(tag))
                    if utag >= 10:
                        print("...Too many object tags unknown...")
                        break
                    utag += 1
                    cnt = unpack('<I', goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                tag = goz_file.read(4)
        bpy.context.view_layer.objects.active = obj #make active last obj

        # if diff:
        #     mtex = objMat.texture_slots.add()
        #     mtex.texture = txtDiff
        #     mtex.texture_coords = 'UV'
        #     mtex.use_map_color_diffuse = True
        # if disp:
        #     mtex = objMat.texture_slots.add()
        #     mtex.texture = txtDisp
        #     mtex.texture_coords = 'UV'
        #     mtex.use_map_color_diffuse = False
        #     mtex.use_map_displacement = True
        # if nmp:
        #     mtex = objMat.texture_slots.add()
        #     mtex.texture = txtNmp
        #     mtex.texture_coords = 'UV'
        #     mtex.use_map_normal = True
        #     mtex.use_map_color_diffuse = False
        #     mtex.normal_factor = 1.
        #     mtex.normal_map_space = 'TANGENT'
        # me.materials.append(objMat)
        return

    def execute(self, context):
        goz_obj_paths = []
        with open(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt", 'rt') as goz_objs_list:
            for line in goz_objs_list:
                goz_obj_paths.append(line.strip() + '.GoZ')

        if len(goz_obj_paths) == 0:
            self.report({'INFO'}, message="No goz files in GoZ_ObjectList.txt")
            return{'CANCELLED'}

        if context.object and context.object.mode != 'OBJECT':
            # ! cant get proper context from timers for now to change mode: https://developer.blender.org/T62074
            bpy.ops.object.mode_set(context.copy(), mode='OBJECT') #hack

        for ztool_path in goz_obj_paths:
            self.GoZit(ztool_path)

        self.report({'INFO'}, "Done")
        return{'FINISHED'}

    def invoke(self, context, event):
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


def create_node_material(mat):
    # enable nodes
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    output_node = nodes.get('Principled BSDF')
    vcol_node = nodes.get('ShaderNodeAttribute')

    # create new node
    if not vcol_node:
        vcol_node = nodes.new('ShaderNodeAttribute')
        vcol_node.location = -300, 200
        vcol_node.attribute_name = 'Col'  # TODO: replace with vertex color group name

        # link nodes
        mat.node_tree.links.new(output_node.inputs[0], vcol_node.outputs[0])


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
        depsgraph = bpy.context.evaluated_depsgraph_get()
        if pref.modifiers == 'APPLY_EXPORT':
            object_eval = obj.evaluated_get(depsgraph)
            # me = object_eval.to_mesh() #with modifiers - crash need to_mesh_clear()?
            me = bpy.data.meshes.new_from_object(object_eval)  # with modifiers
            obj.data = me
            obj.modifiers.clear()
        elif pref.modifiers == 'JUST_EXPORT':
            object_eval = obj.evaluated_get(depsgraph)
            me = bpy.data.meshes.new_from_object(object_eval)
        else:
            me = obj.data

        #DO the triangulation of Ngons only, but do not write it to original object. User has to handle Ngons manaully if they want.
        bm = bmesh.new()
        bm.from_mesh(me)
        triangulate_faces = [f for f in bm.faces if len(f.edges) > 4]
        result = bmesh.ops.triangulate(bm, faces=triangulate_faces)
        #join traingles only that are result of ngon triangulation
        bmesh.ops.join_triangles(bm, faces=result['faces'], cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False, angle_face_threshold=3.1, angle_shape_threshold=3.1)
        export_mesh = bpy.data.meshes.new(name=f'{obj.name}_goz')  # mesh is deleted in main loop anyway
        bm.to_mesh(export_mesh)
        bm.free()

        return export_mesh

    def exportGoZ(self, path, scn, obj, pathImport):
        pref = bpy.context.preferences.addons[__package__.split(".")[0]].preferences

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

        me = self.apply_modifiers(obj, pref)
        me.calc_loop_triangles()

        if pref.flip_y:
            mat_transform = mathutils.Matrix([
                (-1., 0., 0., 0.),
                (0., 0., 1., 0.),
                (0., 1., 0., 0.),
                (0., 0., 0., 1.)])
        else:
            mat_transform = mathutils.Matrix([
                (1., 0., 0., 0.),
                (0., 0., -1., 0.),
                (0., 1., 0., 0.),
                (0., 0., 0., 1.)])

        with open(pathImport+'/{0}.GoZ'.format(obj.name), 'wb') as goz_file:
            goz_file.write(b"GoZb 1.0 ZBrush GoZ Binary")
            goz_file.write(pack('<6B', 0x2E, 0x2E, 0x2E, 0x2E, 0x2E, 0x2E))
            goz_file.write(pack('<I', 1))  # obj tag
            goz_file.write(pack('<I', len(obj.name)+24))
            goz_file.write(pack('<Q', 1))
            goz_file.write(b'GoZMesh_'+obj.name.encode('U8'))
            goz_file.write(pack('<4B', 0x89, 0x13, 0x00, 0x00))
            goz_file.write(pack('<I', 20))
            goz_file.write(pack('<Q', 1))
            goz_file.write(pack('<I', 0))
            nbFaces = len(me.polygons)
            nbVertices = len(me.vertices)
            goz_file.write(pack('<4B', 0x11, 0x27, 0x00, 0x00))
            goz_file.write(pack('<I', nbVertices*3*4+16))
            goz_file.write(pack('<Q', nbVertices))
            for vert in me.vertices:
                modif_coo = obj.matrix_world @ vert.co
                modif_coo = mat_transform @ modif_coo
                goz_file.write(pack('<3f', modif_coo[0], modif_coo[1], modif_coo[2]))
            goz_file.write(pack('<4B', 0x21, 0x4E, 0x00, 0x00))
            goz_file.write(pack('<I', nbFaces*4*4+16))
            goz_file.write(pack('<Q', nbFaces))
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


            # --Polypainting--
            if me.vertex_colors.active:
                vcoldata = me.vertex_colors.active.data # color[loop_id]
                vcolArray = bytearray([0] * nbVertices * 3)
                #fill vcArray(vert_idx + rgb_offset) = color_xyz
                for loop in me.loops: #in the end we will fill verts with last vert_loop color
                    vert_idx = loop.vertex_index
                    vcolArray[vert_idx*3] = int(255*vcoldata[loop.index].color[0])
                    vcolArray[vert_idx*3+1] = int(255*vcoldata[loop.index].color[1])
                    vcolArray[vert_idx*3+2] = int(255*vcoldata[loop.index].color[2])

                goz_file.write(pack('<4B', 0xb9, 0x88, 0x00, 0x00))
                goz_file.write(pack('<I', nbVertices*4+16))
                goz_file.write(pack('<Q', nbVertices))
                for i in range(0, len(vcolArray), 3):
                    goz_file.write(pack('<B', vcolArray[i+2]))
                    goz_file.write(pack('<B', vcolArray[i+1]))
                    goz_file.write(pack('<B', vcolArray[i]))
                    goz_file.write(pack('<B', 0))
                del vcolArray
            # --Mask--
            for vertexGroup in obj.vertex_groups:
                if vertexGroup.name.lower() == 'mask':
                    goz_file.write(pack('<4B', 0x32, 0x75, 0x00, 0x00))
                    goz_file.write(pack('<I', nbVertices*2+16))
                    goz_file.write(pack('<Q', nbVertices))
                    for i in range(nbVertices):
                        try:
                            goz_file.write(pack('<H', int((1.-vertexGroup.weight(i))*65535)))
                        except:
                            goz_file.write(pack('<H', 255))
                    break
            # --Polygroups--
            vertWeight = []
            for i in range(len(me.vertices)):
                vertWeight.append([])
                for group in me.vertices[i].groups:
                    try:
                        if group.weight == 1. and obj.vertex_groups[group.group].name.lower() != 'mask':
                            vertWeight[i].append(group.group)
                    except:
                        print('error reading vertex group data')
            goz_file.write(pack('<4B', 0x41, 0x9C, 0x00, 0x00))
            goz_file.write(pack('<I', nbFaces*2+16))
            goz_file.write(pack('<Q', nbFaces))
            import random
            numrand = random.randint(1, 40)
            for face in me.polygons:
                gr = []
                for vert in face.vertices:
                    gr.extend(vertWeight[vert])
                gr.sort()
                gr.reverse()
                tmp = {}
                groupVal = 0
                for val in gr:
                    if val not in tmp:
                        tmp[val] = 1
                    else:
                        tmp[val] += 1
                        if tmp[val] == len(face.vertices):
                            groupVal = val
                            break
                if obj.vertex_groups.items() != []:
                    grName = obj.vertex_groups[groupVal].name
                    if grName.lower() == 'mask':
                        goz_file.write(pack('<H', 0))
                    else:
                        grName = obj.vertex_groups[groupVal].index * numrand
                        goz_file.write(pack('<H', grName))
                else:
                    goz_file.write(pack('<H', 0))
            # Diff, disp and nm maps
            diff = 0
            disp = 0
            nm = 0
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
            #                         nm = texslot
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
            if nm:
                name = nm.texture.image.filepath.replace('\\', '/')
                name = name.rsplit('/')[-1]
                name = name.rsplit('.')[0]
                if len(name) > 3:
                    if name[-3:] == "_NM":
                        name = path + '/GoZProjects/Default/' + name + '.bmp'
                    else:
                        name = path + '/GoZProjects/Default/' + name + '_NM.bmp'
                nm.texture.image.save_render(name)
                print(name)
                name = name.encode('utf8')
                goz_file.write(pack('<4B', 0x51, 0xc3, 0x00, 0x00))
                goz_file.write(pack('<I', len(name)+16))
                goz_file.write(pack('<Q', 1))
                goz_file.write(pack('%ss' % len(name), name))
            # fin
            scn.render.image_settings.file_format = formatRender
            goz_file.write(pack('16x'))

        bpy.data.meshes.remove(me)
        return

    def execute(self, context):
        exists = os.path.isfile(f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt")
        if not exists:
            print(f'Cant find: {f"{PATHGOZ}/GoZBrush/GoZ_ObjectList.txt"}. Check your Zbrush GOZ installation')
            return {"CANCELLED"}
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
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


class GoBPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    flip_y: bpy.props.BoolProperty(
        name="Invert up axis",
        description="If you experience bad mesh orientation use this option, change mesh export/import orientation mode",
        default=False)
    modifiers: bpy.props.EnumProperty(
        name='Modifiers',
        description='How to handle exported object modifiers',
        items=[('APPLY_EXPORT', 'Export and Apply', 'Apply modifiers to object and export them to zbrush'),
               ('JUST_EXPORT', 'Only Export', 'Export modifiers to zbrush but do not apply them to mesh'),
               ('IGNORE', 'Ignore', 'Do not export modifiers')],
        default='JUST_EXPORT')

    # addon updater preferences
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False)
    updater_intrval_months: bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)
    updater_intrval_days: bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31)
    updater_intrval_hours: bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)
    updater_intrval_minutes: bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'flip_y')
        layout.prop(self, 'modifiers')

        col = layout.column()   # works best if a column, or even just self.layout
        mainrow = layout.row()
        col = mainrow.column()

        # updater draw function
        # could also pass in col as third arg
        addon_updater_ops.update_settings_ui(self, context)
