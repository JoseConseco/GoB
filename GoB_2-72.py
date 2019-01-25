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

import bpy, mathutils, bl_ui, time, os
from struct import pack,unpack
from copy import deepcopy

bl_info = {
    "name": "GoB",
    "description": "An unofficial GOZ-like for Blender",
    "author": "ODe",
    "version": (2, 72),
    "blender": (2, 72, 0),
    "location": "At the info header",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:"
		"2.6/Py/Scripts/Import-Export/GoB_ZBrush_import_export",
    "tracker_url": "http://www.zbrushcentral.com/showthread.php?"
		"127419-GoB-an-unofficial-GoZ-for-Blender",
    "category": "Import-Export"}

if os.path.isfile("C:/Users/Public/Pixologic/GoZBrush/GoZBrushFromApp.exe"):
    PATHGOZ = "C:/Users/Public/Pixologic"
    FROMAPP = "GoZBrushFromApp.exe"
elif os.path.isfile("/Users/Shared/Pixologic/GoZBrush/GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"):
    PATHGOZ = "/Users/Shared/Pixologic"
    FROMAPP = "GoZBrushFromApp.app/Contents/MacOS/GoZBrushFromApp"
else:PATHGOZ = False


autoload = 0.8 # Check GoZ export every 0.8 seconds
importToggle = False
objectList = []
varTime = time.time() - 240.0 
    
class INFO_HT_header(bpy.types.Header):
    bl_space_type = 'INFO'

    def draw(self, context):
        global importToggle
        layout = self.layout

        window = context.window
        scene = context.scene
        rd = scene.render

        row = layout.row(align=True)
        row.template_header()

        INFO_MT_editor_menus.draw_collapsible(context, layout)

        if window.screen.show_fullscreen:
            layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")
            layout.separator()
        else:
            layout.template_ID(context.window, "screen", new="screen.new", unlink="screen.delete")
            layout.template_ID(context.screen, "scene", new="scene.new", unlink="scene.delete")

        layout.separator()

        if rd.has_multiple_engines:
            layout.prop(rd, "engine", text="")

        layout.separator()

        layout.template_running_jobs()

        layout.template_reports_banner()

        row = layout.row(align=True)

        if bpy.app.autoexec_fail is True and bpy.app.autoexec_fail_quiet is False:
            row.label("Auto-run disabled: %s" % bpy.app.autoexec_fail_message, icon='ERROR')
            if bpy.data.is_saved:
                props = row.operator("wm.revert_mainfile", icon='SCREEN_BACK', text="Reload Trusted")
                props.use_scripts = True

            row.operator("script.autoexec_warn_clear", text="Ignore")
            return

        row.operator(
                operator="scene.gob_export",
                text="",
                icon='BRUSH_PINCH',
                emboss=False)
        if importToggle:
            row.operator(
                    operator="scene.gob_import",
                    text="",
                    icon='MATCAP_21',
                    emboss=False)
        else:
            row.operator(
                    operator="scene.gob_import",
                    text="",
                    icon='MATCAP_07',
                    emboss=False)
        row.label(text=scene.statistics(), translate=False)

class INFO_MT_editor_menus(bpy.types.Menu):
    bl_idname = "INFO_MT_editor_menus"
    bl_label = ""

    def draw(self, context):
        self.draw_menus(self.layout, context)

    @staticmethod
    def draw_menus(layout, context):
        scene = context.scene
        rd = scene.render

        layout.menu("INFO_MT_file")

        if rd.use_game_engine:
            layout.menu("INFO_MT_game")
        else:
            layout.menu("INFO_MT_render")

        layout.menu("INFO_MT_window")
        layout.menu("INFO_MT_help")


class GoB_import(bpy.types.Operator):
    bl_idname = "scene.gob_import"
    bl_label = "Import from Zbrush"

    
    def GoZit(self, pathFile):
        scn = bpy.context.scene
        diff = False
        disp = False
        nmp = False
        utag = 0
        vertsData = []
        facesData = []
        polypaint = []
        try:
            fic = open(pathFile,'rb')
        except:
            return
        fic.seek(36,0)
        lenObjName = unpack('<I',fic.read(4))[0] - 16
        fic.seek(8,1)
        objName = unpack('%ss'%lenObjName,fic.read(lenObjName))[0]
        print(objName.decode('utf-8'))
        objName = objName[8:].decode('utf-8')
        me = bpy.data.meshes.new(objName)
        tag = fic.read(4)
        while tag:
            if tag == b'\x89\x13\x00\x00':
                cnt = unpack('<L',fic.read(4))[0] - 8
                fic.seek(cnt,1)
            elif tag == b'\x11\x27\x00\x00': #Vertices
                fic.seek(4,1)
                cnt = unpack('<Q',fic.read(8))[0]
                me.vertices.add(cnt)
                for i in range(cnt*3):
                    vertsData.append(unpack('<f',fic.read(4))[0])
                me.vertices.foreach_set("co", vertsData)
                del vertsData
            elif tag == b'\x21\x4e\x00\x00': #Faces
                fic.seek(4,1)
                cnt = unpack('<Q',fic.read(8))[0]
                me.tessfaces.add(cnt)
                for i in range(cnt):
                    v1 = unpack('<L',fic.read(4))[0]
                    v2 = unpack('<L',fic.read(4))[0]
                    v3 = unpack('<L',fic.read(4))[0]
                    v4 = unpack('<L',fic.read(4))[0]
                    if v4 == 0xffffffff:
                        facesData.append(v1)
                        facesData.append(v2)
                        facesData.append(v3)
                        facesData.append(0)
                    elif v4 == 0:
                        facesData.append(v4)
                        facesData.append(v1)
                        facesData.append(v2)
                        facesData.append(v3)
                    else:
                        facesData.append(v1)
                        facesData.append(v2)
                        facesData.append(v3)
                        facesData.append(v4)
                me.tessfaces.foreach_set("vertices_raw",facesData)
                del facesData
            elif tag == b'\xa9\x61\x00\x00': #UVs
                me.tessface_uv_textures.new()
                fic.seek(4,1)
                cnt = unpack('<Q',fic.read(8))[0]
                for i in range(cnt):
                    uvFace = me.tessface_uv_textures[0].data[i]
                    x,y = unpack('<2f',fic.read(8))
                    uvFace.uv1 = (x,1.-y)
                    x,y = unpack('<2f',fic.read(8))
                    uvFace.uv2 = (x,1.-y)
                    x,y = unpack('<2f',fic.read(8))
                    uvFace.uv3 = (x,1.-y)
                    x,y = unpack('<2f',fic.read(8))
                    uvFace.uv4 = (x,1.-y)
            elif tag == b'\xb9\x88\x00\x00': #Polypainting
                break
            elif tag == b'\x32\x75\x00\x00': #Mask
                break
            elif tag == b'\x41\x9c\x00\x00': #Polyroups
                break
            elif tag == b'\x00\x00\x00\x00': #End
                break
            else:
                print("unknown tag:{0}\ntry to skip it...".format(tag))
                if utag >= 10:
                    print("...Too many mesh tags unknown...")
                    break
                utag+=1
                cnt = unpack('<I',fic.read(4))[0] - 8
                fic.seek(cnt,1)
            tag = fic.read(4)
        me.transform(mathutils.Matrix([
                            (1., 0.,0.,0.),
                            (0., 0.,1.,0.),
                            (0.,-1.,0.,0.),
                            (0., 0.,0.,1.)]))
        if objName in scn.objects:
            ob = scn.objects[objName]
            backupMatrix=deepcopy(ob.matrix_world)

            oldMesh = ob.data.name

            instances= [obj for obj in bpy.data.objects if obj.data==ob.data]
            for instance in instances:
                instance.data = me

            me.update(calc_tessface=True)
            utag = 0
            while tag:
                if tag == b'\xb9\x88\x00\x00': #Polypainting
                    min = 255
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    for i in range(cnt):
                        data = unpack('<3B',fic.read(3))
                        unpack('<B',fic.read(1)) # Alpha
                        if data[0] < min:min = data[0]
                        polypaint.append(data)
                    if min < 250:
                        vertexColor = me.vertex_colors.new()
                        iv = 0
                        for poly in me.polygons:
                            for loop_index in poly.loop_indices:
                                loop = me.loops[loop_index]
                                v = loop.vertex_index
                                color = polypaint[v]
                                vertexColor.data[iv].color = mathutils.Color([color[2]/255,color[1]/255,color[0]/255])
                                iv+=1
                    del polypaint
                elif tag == b'\x32\x75\x00\x00': #Mask
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    if 'mask' in ob.vertex_groups:
                        ob.vertex_groups.remove(ob.vertex_groups['mask'])
                    groupMask = ob.vertex_groups.new('mask')
                    for i in range(cnt):
                        data = unpack('<H',fic.read(2))[0] /65535.
                        groupMask.add([i],1.-data,'ADD')
                elif tag == b'\x41\x9c\x00\x00': #Polyroups
                    groups = []
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    for i in range(cnt):
                        gr = unpack('<H',fic.read(2))[0]
                        #continue # <- Skip polygroups
                        if gr not in groups:
                            if str(gr) in ob.vertex_groups:
                                ob.vertex_groups.remove(ob.vertex_groups[str(gr)])
                            polygroup = ob.vertex_groups.new(str(gr))
                            groups.append(gr)
                        else:
                            polygroup = ob.vertex_groups[str(gr)]
                        for j in range(len(me.tessfaces[i].vertices_raw)):
                            polygroup.add([me.tessfaces[i].vertices_raw[j]],1.,'ADD')
                    try:ob.vertex_groups.remove(ob.vertex_groups.get('0'))
                    except:pass
                elif tag == b'\x00\x00\x00\x00':break #End
                elif tag == b'\xc9\xaf\x00\x00': #Diff map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    diffName = unpack('%ss'%cnt,fic.read(cnt))[0].decode('utf-8')
                    diff = True
                elif tag == b'\xd9\xd6\x00\x00': #Disp map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    dispName = unpack('%ss'%cnt,fic.read(cnt))[0].decode('utf-8')
                    disp = True
                elif tag == b'\x51\xc3\x00\x00': #Normal map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    nmpName = unpack('%ss'%cnt,fic.read(cnt))[0].decode('utf-8')
                    nmp = True
                else:
                    print("unknown tag:{0}\ntry to skip it...".format(tag))
                    if utag >= 10:
                        print("...Too many object tags unknown...")
                        break
                    utag+=1
                    cnt = unpack('<I',fic.read(4))[0] - 8
                    fic.seek(cnt,1)
                tag = fic.read(4)
            fic.close()
            ob.select = True
            scn.objects.active = ob
            GoBmat = False
            slotDiff = 0
            slotDisp = 0
            slotNm = 0

            ob.matrix_world = backupMatrix
            ob.data.transform(backupMatrix.inverted())
            for matslot in bpy.data.meshes[oldMesh].materials:
                ob.data.materials.append(matslot)
            if ob.material_slots.items():
                for matslot in ob.material_slots:
                    if matslot.material:
                        for texslot in matslot.material.texture_slots:
                            if texslot:
                                if texslot.texture:
                                    if texslot.texture.type == 'IMAGE' and texslot.texture_coords == 'UV' and texslot.texture.image:
                                        if texslot.use_map_color_diffuse:slotDiff=texslot
                                        if texslot.use_map_displacement:slotDisp=texslot
                                        if texslot.use_map_normal:slotNm=texslot
                        GoBmat = matslot.material
                        break
            if diff:
                if slotDiff:
                    if bpy.path.display_name_from_filepath(slotDiff.texture.image.filepath) == bpy.path.display_name_from_filepath(diffName):
                        slotDiff.texture.image.reload()
                        print("Image reloaded")
                    else:
                        slotDiff.texture.image = bpy.data.images.load(diffName)
                else:
                    if not GoBmat:
                        GoBmat = bpy.data.materials.new('GoB_{0}'.format(objName))
                        me.materials.append(GoBmat)
                    mtex = GoBmat.texture_slots.add()
                    mtex.texture = bpy.data.textures.new("GoB_diffuse",'IMAGE')
                    mtex.texture.image = bpy.data.images.load(diffName)
                    mtex.texture_coords = 'UV'
                    mtex.use_map_color_diffuse = True
            if disp:
                if slotDisp:
                    if bpy.path.display_name_from_filepath(slotDisp.texture.image.filepath) == bpy.path.display_name_from_filepath(dispName):
                        slotDisp.texture.image.reload()
                    else:
                        slotDisp.texture.image = bpy.data.images.load(dispName)
                else:
                    if not GoBmat:
                        GoBmat = bpy.data.materials.new('GoB_{0}'.format(objName))
                        me.materials.append(GoBmat)
                    mtex = GoBmat.texture_slots.add()
                    mtex.texture = bpy.data.textures.new("GoB_displacement",'IMAGE')
                    mtex.texture.image = bpy.data.images.load(dispName)
                    mtex.texture_coords = 'UV'
                    mtex.use_map_color_diffuse = False
                    mtex.use_map_displacement = True
            if nmp:
                if slotNm:
                    if bpy.path.display_name_from_filepath(slotNm.texture.image.filepath) == bpy.path.display_name_from_filepath(nmpName):
                        slotNm.texture.image.reload()
                    else:
                        slotNm.texture.image = bpy.data.images.load(nmpName)
                else:
                    if not GoBmat:
                        GoBmat = bpy.data.materials.new('GoB_{0}'.format(objName))
                        me.materials.append(GoBmat)
                    mtex = GoBmat.texture_slots.add()
                    mtex.texture = bpy.data.textures.new("GoB_normal",'IMAGE')
                    mtex.texture.image = bpy.data.images.load(nmpName)
                    mtex.texture_coords = 'UV'
                    mtex.use_map_normal = True
                    mtex.use_map_color_diffuse = False
                    mtex.normal_factor = 1.
                    mtex.normal_map_space = 'TANGENT'
        else:
            me.update(calc_tessface=True)
            ob = bpy.data.objects.new(objName, me)
            scn.objects.link(ob)
            utag = 0
            while tag:
                if tag == b'\xb9\x88\x00\x00': #Polypainting
                    min = 255
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    for i in range(cnt):
                        data = unpack('<3B',fic.read(3))
                        unpack('<B',fic.read(1)) # Alpha
                        if data[0] < min:min = data[0]
                        polypaint.append(data)
                    if min < 250:
                        vertexColor = me.vertex_colors.new()
                        iv = 0
                        for poly in me.polygons:
                            for loop_index in poly.loop_indices:
                                loop = me.loops[loop_index]
                                v = loop.vertex_index
                                color = polypaint[v]
                                vertexColor.data[iv].color = mathutils.Color([color[2]/255,color[1]/255,color[0]/255])
                                iv+=1
                elif tag == b'\x32\x75\x00\x00': #Mask
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    groupMask = ob.vertex_groups.new('mask')
                    for i in range(cnt):
                        data = unpack('<H',fic.read(2))[0] /65535.
                        groupMask.add([i],1.-data,'ADD')
                elif tag == b'\x41\x9c\x00\x00': #Polyroups
                    groups = []
                    fic.seek(4,1)
                    cnt = unpack('<Q',fic.read(8))[0]
                    for i in range(cnt):
                        gr = unpack('<H',fic.read(2))[0]
                        if gr not in groups:
                            polygroup = ob.vertex_groups.new(str(gr))
                            groups.append(gr)
                        else:
                            polygroup = ob.vertex_groups[str(gr)]
                        for j in range(len(me.tessfaces[i].vertices_raw)):
                            polygroup.add([me.tessfaces[i].vertices_raw[j]],1.,'ADD')
                    try:ob.vertex_groups.remove(ob.vertex_groups.get('0'))
                    except:pass
                elif tag == b'\x00\x00\x00\x00':break #End
                elif tag == b'\xc9\xaf\x00\x00': #Diff map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    diffName = unpack('%ss'%cnt,fic.read(cnt))[0]
                    print(diffName.decode('utf-8'))
                    img = bpy.data.images.load(diffName.strip().decode('utf-8'))
                    diff = True
                    txtDiff = bpy.data.textures.new("GoB_diffuse",'IMAGE')
                    txtDiff.image = img
                    me.uv_textures[0].data[0].image = img
                elif tag == b'\xd9\xd6\x00\x00': #Disp map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    dispName = unpack('%ss'%cnt,fic.read(cnt))[0]
                    print(dispName.decode('utf-8'))
                    img = bpy.data.images.load(dispName.strip().decode('utf-8'))
                    disp = True
                    txtDisp = bpy.data.textures.new("GoB_displacement",'IMAGE')
                    txtDisp.image = img
                elif tag == b'\x51\xc3\x00\x00': #Normal map
                    cnt = unpack('<I',fic.read(4))[0] - 16
                    fic.seek(8,1)
                    nmpName = unpack('%ss'%cnt,fic.read(cnt))[0]
                    print(nmpName.decode('utf-8'))
                    img = bpy.data.images.load(nmpName.strip().decode('utf-8'))
                    nmp = True
                    txtNmp = bpy.data.textures.new("GoB_normal",'IMAGE')
                    txtNmp.image = img
                    txtNmp.use_normal_map = True
                else:
                    print("unknown tag:{0}\ntry to skip it...".format(tag))
                    if utag >= 10:
                        print("...Too many object tags unknown...")
                        break
                    utag+=1
                    cnt = unpack('<I',fic.read(4))[0] - 8
                    fic.seek(cnt,1)
                tag = fic.read(4)
            fic.close()
            ob.select = True
            scn.objects.active = ob
            objMat = bpy.data.materials.new('GoB_{0}'.format(objName))
            if diff:
                mtex = objMat.texture_slots.add()
                mtex.texture = txtDiff
                mtex.texture_coords = 'UV'
                mtex.use_map_color_diffuse = True
            if disp:
                mtex = objMat.texture_slots.add()
                mtex.texture = txtDisp
                mtex.texture_coords = 'UV'
                mtex.use_map_color_diffuse = False
                mtex.use_map_displacement = True
            if nmp:
                mtex = objMat.texture_slots.add()
                mtex.texture = txtNmp
                mtex.texture_coords = 'UV'
                mtex.use_map_normal = True
                mtex.use_map_color_diffuse = False
                mtex.normal_factor = 1.
                mtex.normal_map_space = 'TANGENT'
            me.materials.append(objMat)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    def execute(self, context):
        global varTime, objectList

        try:
            ficTime = os.path.getmtime(
                    "{0}/GoZBrush/GoZ_ObjectList.txt".format(PATHGOZ))
        except:
            print("{0}/GoZBrush/GoZ_ObjectList.txt unreadable".format(PATHGOZ))
            return{'CANCELLED'}
        # print("\n\t------")
        if ficTime > varTime:
            objectList = []
            for line in open("{0}/GoZBrush/GoZ_ObjectList.txt".format(PATHGOZ),'rt'):
                objectList.append(line.strip() + '.GoZ')
            varTime = ficTime
        else:
            if importToggle:
                self.report({'INFO'},"Nothing to update")
                print("Nothing to update")
                return{'CANCELLED'}
        if len(objectList) == 0:
            self.report({'INFO'}, message="No update")
            return{'CANCELLED'}
        for objPath in objectList:
            self.GoZit(objPath)
        self.report({'INFO'},"Done")
        return{'FINISHED'}

    def invoke(self, context, event):
        global importToggle

        if event.shift:
            if importToggle == False:
                return self.execute(context)
            return{'FINISHED'}
        elif not importToggle:
            bpy.ops.wm.gob_timer()
        importToggle = not importToggle
        return{'FINISHED'}


class GoB_export(bpy.types.Operator):
    bl_idname = "scene.gob_export"
    bl_label = "Export to Zbrush"

    def exportGoZ(self, path,scn,ob,pathImport):
        import random
        if bpy.context.object.type=='MESH':
            bpy.ops.object.convert(target='MESH')

        me = ob.to_mesh(scn,False,'PREVIEW')
        mat_transform = mathutils.Matrix([
                                (1.,0., 0.,0.),
                                (0.,0.,-1.,0.),
                                (0.,1., 0.,0.),
                                (0.,0., 0.,1.)])
        fic = open(pathImport+'/{0}.GoZ'.format(ob.name),'wb')
        fic.write(b"GoZb 1.0 ZBrush GoZ Binary")
        fic.write(pack('<6B',0x2E,0x2E,0x2E,0x2E,0x2E,0x2E))
        fic.write(pack('<I',1)) #obj tag
        fic.write(pack('<I',len(ob.name)+24))
        fic.write(pack('<Q',1))
        fic.write(b'GoZMesh_'+ob.name.encode('U8'))
        fic.write(pack('<4B',0x89,0x13,0x00,0x00))
        fic.write(pack('<I',20))
        fic.write(pack('<Q',1))
        fic.write(pack('<I',0))
        nbFaces = len(me.tessfaces)
        nbVertices = len(me.vertices)
        fic.write(pack('<4B',0x11,0x27,0x00,0x00))
        fic.write(pack('<I',nbVertices*3*4+16))
        fic.write(pack('<Q',nbVertices))
        for vert in me.vertices:
            modif_coo = ob.matrix_world * vert.co
            modif_coo = mat_transform * modif_coo
            fic.write(pack('<3f',modif_coo[0],modif_coo[1],modif_coo[2]))
        fic.write(pack('<4B',0x21,0x4E,0x00,0x00))
        fic.write(pack('<I',nbFaces*4*4+16))
        fic.write(pack('<Q',nbFaces))
        for face in me.tessfaces:
            if len(face.vertices) == 4:
                fic.write(pack('<4I',face.vertices[0],
                                    face.vertices[1],
                                    face.vertices[2],
                                    face.vertices[3]))
            elif len(face.vertices) == 3:
                fic.write(pack('<3I4B',face.vertices[0],
                                    face.vertices[1],
                                    face.vertices[2],
                                    0xFF,0xFF,0xFF,0xFF))
        # --UVs--
        if me.tessface_uv_textures.active:
            uvdata = me.tessface_uv_textures.active.data
            fic.write(pack('<4B',0xA9,0x61,0x00,0x00))
            fic.write(pack('<I',len(uvdata)*4*2*4+16))
            fic.write(pack('<Q',len(uvdata)))
            for uvface in uvdata:
                fic.write(pack('<8f',uvface.uv_raw[0],
                                    1.-uvface.uv_raw[1],
                                    uvface.uv_raw[2],
                                    1.-uvface.uv_raw[3],
                                    uvface.uv_raw[4],
                                    1.-uvface.uv_raw[5],
                                    uvface.uv_raw[6],
                                    1.-uvface.uv_raw[7]))
        # --Polypainting--
        if me.tessface_vertex_colors.active:
            vcoldata =  me.tessface_vertex_colors.active.data
            vcolArray = bytearray([0]*nbVertices*3)
            for i in range(len((vcoldata))):
                vcolArray[me.tessfaces[i].vertices[0]*3] = int(255*vcoldata[i].color1[0])
                vcolArray[me.tessfaces[i].vertices[0]*3+1] = int(255*vcoldata[i].color1[1])
                vcolArray[me.tessfaces[i].vertices[0]*3+2] = int(255*vcoldata[i].color1[2])
                vcolArray[me.tessfaces[i].vertices[1]*3] = int(255*vcoldata[i].color2[0])
                vcolArray[me.tessfaces[i].vertices[1]*3+1] = int(255*vcoldata[i].color2[1])
                vcolArray[me.tessfaces[i].vertices[1]*3+2] = int(255*vcoldata[i].color2[2])
                vcolArray[me.tessfaces[i].vertices[2]*3] = int(255*vcoldata[i].color3[0])
                vcolArray[me.tessfaces[i].vertices[2]*3+1] = int(255*vcoldata[i].color3[1])
                vcolArray[me.tessfaces[i].vertices[2]*3+2] = int(255*vcoldata[i].color3[2])
                if len(me.tessfaces[i].vertices) == 4:
                    vcolArray[me.tessfaces[i].vertices[3]*3] = int(255*vcoldata[i].color4[0])
                    vcolArray[me.tessfaces[i].vertices[3]*3+1] = int(255*vcoldata[i].color4[1])
                    vcolArray[me.tessfaces[i].vertices[3]*3+2] = int(255*vcoldata[i].color4[2])
            fic.write(pack('<4B',0xb9,0x88,0x00,0x00))
            fic.write(pack('<I',nbVertices*4+16))
            fic.write(pack('<Q',nbVertices))
            for i in range(0,len(vcolArray),3):
                fic.write(pack('<B',vcolArray[i+2]))
                fic.write(pack('<B',vcolArray[i+1]))
                fic.write(pack('<B',vcolArray[i]))
                fic.write(pack('<B',0))
            del vcolArray
        # --Mask--
        for vertexGroup in ob.vertex_groups:
            if vertexGroup.name.lower() == 'mask':
                fic.write(pack('<4B',0x32,0x75,0x00,0x00))
                fic.write(pack('<I',nbVertices*2+16))
                fic.write(pack('<Q',nbVertices))
                for i in range(nbVertices):
                    try:fic.write(pack('<H',int((1.-vertexGroup.weight(i))*65535)))
                    except:fic.write(pack('<H',255))
                break
        # --Polygroups--
        vertWeight = []
        for i in range(len(me.vertices)):
            vertWeight.append([])
            for group in me.vertices[i].groups:
                try:
                    if group.weight == 1. and ob.vertex_groups[group.group].name.lower() != 'mask':
                        vertWeight[i].append(group.group)
                except:
                    print('error reading vertex group data')
        fic.write(pack('<4B',0x41,0x9C,0x00,0x00))
        fic.write(pack('<I',nbFaces*2+16))
        fic.write(pack('<Q',nbFaces))
        numrand = random.randint(1,40)
        for face in me.tessfaces:
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
                    tmp[val] +=1
                    if tmp[val] == len(face.vertices):
                        groupVal = val
                        break
            if ob.vertex_groups.items() != []:
                grName = ob.vertex_groups[groupVal].name
                if grName.lower() == 'mask':
                    fic.write(pack('<H',0))
                else:
                    grName = ob.vertex_groups[groupVal].index * numrand
                    fic.write(pack('<H',grName))
            else:fic.write(pack('<H',0))
        # Diff, disp and nm maps
        diff = 0
        disp = 0
        nm = 0
        GoBmat = False
        for matslot in ob.material_slots:
            if matslot.material:
                GoBmat = matslot
                break

        try:
            if GoBmat:
                for texslot in GoBmat.material.texture_slots:
                    if texslot:
                        if texslot.texture:
                                if texslot.texture.type == 'IMAGE' and texslot.texture_coords == 'UV' and texslot.texture.image:
                                    if texslot.use_map_color_diffuse:diff=texslot
                                    if texslot.use_map_displacement:disp=texslot
                                    if texslot.use_map_normal:nm=texslot
            formatRender = scn.render.image_settings.file_format
            scn.render.image_settings.file_format = 'BMP'
            if diff:
                name = diff.texture.image.filepath.replace('\\','/')
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
                fic.write(pack('<4B',0xc9,0xaf,0x00,0x00))
                fic.write(pack('<I',len(name)+16))
                fic.write(pack('<Q',1))
                fic.write(pack('%ss'%len(name),name))
            if disp:
                name = disp.texture.image.filepath.replace('\\','/')
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
                fic.write(pack('<4B',0xd9,0xd6,0x00,0x00))
                fic.write(pack('<I',len(name)+16))
                fic.write(pack('<Q',1))
                fic.write(pack('%ss'%len(name),name))
            if nm:
                name = nm.texture.image.filepath.replace('\\','/')
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
                fic.write(pack('<4B',0x51,0xc3,0x00,0x00))
                fic.write(pack('<I',len(name)+16))
                fic.write(pack('<Q',1))
                fic.write(pack('%ss'%len(name),name))
            # fin
        except:
            # continue even when no textures are found
            pass

        scn.render.image_settings.file_format = formatRender
        fic.write(pack('16x'))
        fic.close()
        bpy.data.meshes.remove(me)
        return

    def execute(self,context):
        global varTime

        scn = bpy.context.scene
        fic = open("{0}/GoZBrush/GoZ_ObjectList.txt".format(PATHGOZ),'wt')
        for obj in scn.objects:
            if obj.type == 'MESH' and obj.select:
                obj.name = obj.name.replace('.','_')
                obj.name = obj.name.replace(' ','_')
                bpy.ops.object.mode_set(mode='OBJECT')
                self.exportGoZ(
                    PATHGOZ, scn, obj,
                    '{0}/GoZProjects/Default'.format(PATHGOZ))
                ztn = open(
                    "{0}/GoZProjects/Default/{1}.ztn".format(PATHGOZ,obj.name),'wt')
                ztn.write('{0}/GoZProjects/Default/{1}'.format(PATHGOZ, obj.name))
                ztn.close()
                fic.write(
                    '{0}/GoZProjects/Default/{1}\n'.format(PATHGOZ, obj.name))
        fic.close()
        varTime = os.path.getmtime(
                        "{0}/GoZBrush/GoZ_ObjectList.txt".format(PATHGOZ))
        os.system("{0}/GoZBrush/{1}".format(PATHGOZ,FROMAPP))
        return{'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class GoB_ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.gob_timer"
    bl_label = "Modal Timer Operator for GoB"

    _timer = None

    def modal(self, context, event):
        global importToggle

        if not importToggle:return self.cancel(context)
        if event.type == 'TIMER':bpy.ops.scene.gob_import()
        return {'PASS_THROUGH'}

    def execute(self, context):
        self._timer = context.window_manager.event_timer_add(
            autoload, context.window)
        context.window_manager.modal_handler_add(self)
        # print("running")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}


def register():
    bpy.utils.register_class(GoB_export)
    bpy.utils.register_class(GoB_import)
    bpy.utils.register_class(INFO_HT_header)
    # bpy.utils.register_class(bl_ui.space_info.INFO_MT_editor_menus)
    bpy.utils.register_class(GoB_ModalTimerOperator)

def unregister():
    import bl_ui

    bpy.utils.unregister_class(GoB_export)
    bpy.utils.unregister_class(GoB_import)
    bpy.utils.unregister_class(INFO_HT_header)
    bpy.utils.register_class(bl_ui.space_info.INFO_HT_header)
    bpy.utils.unregister_class(GoB_ModalTimerOperator)

if __name__ == "__main__":
    if PATHGOZ:register()