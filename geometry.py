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
import math
from bpy.types import Object
from . import utils, output


def get_vertex_colors(obj: Object, numVertices):
    
  mesh = obj.data
  vcolArray = bytearray([0] * numVertices * 3) 

  active_color = mesh.color_attributes.active_color 
  color_attribute = mesh.attributes.get(active_color.name, None)

  # Pre-calculate vertex base indices for faster access
  vertex_indices = [i * 3 for i in range(numVertices)]

  for vert, vertex_index in zip(mesh.vertices, vertex_indices):
    color_data = color_attribute.data[vert.index]
    color = color_data.color_srgb

    vcolArray[vertex_index] = int(255 * color[0])
    vcolArray[vertex_index + 1] = int(255 * color[1])
    vcolArray[vertex_index + 2] = int(255 * color[2])
  
  return vcolArray


def apply_transformation(me, is_import=True): 
    mat_transform = None
    scale = 1.0
    
    if utils.prefs().use_scale == 'BUNITS':
        scale = 1 / bpy.context.scene.unit_settings.scale_length

    if utils.prefs().use_scale == 'MANUAL':        
        scale =  1 / utils.prefs().manual_scale

    if utils.prefs().use_scale == 'ZUNITS':
        if bpy.context.active_object:
            obj = bpy.context.active_object
            i, max = utils.max_list_value(obj.dimensions)
            scale =  1 / utils.prefs().zbrush_scale * max
            if utils.prefs().debug_output:
                print("unit scale 2: ", obj.dimensions, i, max, scale, obj.dimensions * scale)
            
    #import
    if utils.prefs().flip_up_axis:  # fixes bad mesh orientation for some people
        if utils.prefs().flip_forward_axis:
            if is_import:
                me.transform(mathutils.Matrix([
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * scale
                )
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * (1/scale)
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (-1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * scale
                )
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * (1/scale)
    
    else:
        if utils.prefs().flip_forward_axis:            
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (-1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * scale
                )
                #me.flip_normals()
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (-1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * (1/scale)
        else:
            if is_import:
                #import
                me.transform(mathutils.Matrix([
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, -1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * scale
                )
            else:
                #export
                mat_transform = mathutils.Matrix([
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 0.0, -1.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0)]) * (1/scale)
    
    return me, mat_transform


def mesh_welder(obj, d = 0.0001):    
    " merges vertices that are closer than d to each other" 
    d = utils.prefs().export_merge_distance
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=d)
    bm.to_mesh(obj.data)  
    bm.free()


def restore_selection(selected, active):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in selected:
        bpy.data.objects[ob.name].select_set(state=True)
    bpy.context.view_layer.objects.active = active


def remove_internal_faces(obj): 

    "remove internal non-manifold faces where all edges have more than 2 face users https://github.com/JoseConseco/GoB/issues/210"  
    if utils.prefs().export_remove_internal_faces:     
        #remember whats selected
        selected = bpy.context.selected_objects
        active = bpy.context.active_object
        
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(state=True) 
        bpy.context.view_layer.objects.active = obj
        last_context = obj.mode
        last_select_mode = bpy.ops.mesh.select_mode
        if utils.prefs().debug_output:
            print("last_context: ", last_context, last_select_mode)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=True, 
                                use_expand=False,
                                type='VERT', 
                                action='ENABLE')   

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_interior_faces() #Select faces where all edges have more than 2 face users
        bpy.ops.mesh.select_non_manifold(extend=True, 
                                        use_wire=True, 
                                        use_boundary=False, 
                                        use_multi_face=True, 
                                        use_non_contiguous=True, #Non Contiguous, Edges between faces pointing in alternate directions
                                        use_verts=True)
                                        
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode=last_context)
        restore_selection(selected, active)


def apply_modifiers(obj):  

    if utils.prefs().performance_profiling: 
        print("\\_____")
        start_time = output.profiler(time.perf_counter(), f"Export Profiling: {obj.name}")
        start_total_time = output.profiler(time.perf_counter(), "")

    depsgraph = bpy.context.evaluated_depsgraph_get()  
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh depsgraph")
        
    object_eval = obj.evaluated_get(depsgraph)   
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh object_eval")

    if utils.prefs().export_modifiers == 'APPLY_EXPORT':      
        mesh_tmp = bpy.data.meshes.new_from_object(object_eval) 
        obj.data = mesh_tmp
        obj.modifiers.clear() 

    elif utils.prefs().export_modifiers == 'ONLY_EXPORT':
        mesh_tmp = object_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)   
        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh to_mesh") 

    else:
        mesh_tmp = obj.data

    #DO the triangulation of Ngons only, but do not write it to original object.    
    bm = bmesh.new()
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh bmesh new")

    bm.from_mesh(mesh_tmp)    
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh bmesh")

    #join traingles only that are result of ngon triangulation 
    facesTotTriangulate = [f for f in bm.faces if len(f.edges) > 4]   
    if facesTotTriangulate:
        result = bmesh.ops.triangulate(bm, faces=facesTotTriangulate) 
        bmesh.ops.join_triangles(
            bm, faces = result['faces'], 
            cmp_seam=False, cmp_sharp=False, cmp_uvs=False, 
            cmp_vcols=False,cmp_materials=False, 
            angle_face_threshold=(math.pi), angle_shape_threshold=(math.pi)) 


        if utils.prefs().performance_profiling: 
            start_time = output.profiler(start_time, "Make Mesh triangulate1")
    
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh triangulate2")

    export_mesh = bpy.data.meshes.new(name=f'{obj.name}_goz')  # mesh is deleted in main loop
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh export_mesh")

    bm.to_mesh(export_mesh)
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh to_mesh")

    bm.free()     
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh bm free")  

    obj.to_mesh_clear()
    if utils.prefs().performance_profiling: 
        start_time = output.profiler(start_time, "Make Mesh to_mesh_clear")  
    
    if utils.prefs().performance_profiling:         
        output.profiler(start_total_time, "Make Mesh return\n _____/") 
   
    return export_mesh    


def process_linked_objects(obj):  

    """ TODO: when linked system is finalized it could be possible to provide
    #  a option to modify the linked object. for now a copy
    #  of the linked object is created to goz it """        
    if obj.library:
        new_obj = obj.copy()
        new_obj.data = obj.data.copy()
        bpy.context.view_layer.active_layer_collection.collection.objects.link(new_obj)
        new_obj.select_set(state=True)
        obj.select_set(state=False)
        bpy.context.view_layer.objects.active = new_obj


def clone_as_object(obj, link=True):

    " create a new object from a exiting one"
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_to_clone = obj.evaluated_get(depsgraph)
    #mesh_clone = obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph) 
    mesh_clone = bpy.data.meshes.new_from_object(obj_to_clone)
    mesh_clone.transform(obj.matrix_world)
    obj_clone = bpy.data.objects.new((obj.name + '_' + obj.type), mesh_clone)  
    if link:
        bpy.context.view_layer.active_layer_collection.collection.objects.link(obj_clone) 
   
    return obj_clone


def check_export_candidates(obj):
    
    if obj.type in {'MESH'}:
        if not utils.prefs().export_modifiers in {'IGNORE'}:
            if obj.modifiers:
                for modifier in obj.modifiers:
                    geometry_modifiers=['Skin', 'Screw']
                    if modifier.name in geometry_modifiers and modifier.show_viewport:
                        # a mesh can have 0 faces but a modifier which adds polygons which makes is a valid export object
                        #print("numfaces 0, skin modifier: ", modifier.name in ['Skin'] and modifier.show_viewport)
                        return modifier.name in geometry_modifiers and modifier.show_viewport   
                    else:
                        # when the modifier is disabled
                        # - it can result in 0 faces which makes it a invalid export candidate
                        # - or in a mesh with more than 0 faces which makes it a valid export candidate
                        numFaces = len(obj.data.polygons)  
                        #print("numfaces 1, no skin modifiers: ", numFaces) 
            else: 
                #when a object has no modifiers, enable export when it has polygons, else disable
                numFaces = len(obj.data.polygons) 
                #print("numfaces 2 modifier export: ", numFaces)
        
        else:
            # if export modifers is Ignored check for polygons to identify export candidates
            numFaces = len(obj.data.polygons)
            #print("numfaces 3 no active modifiers: ", numFaces)

    elif obj.type in {'SURFACE', 'FONT', 'META'}: 
        #allow export for non mesh type objects 
        return True

    elif obj.type in {'CURVE'}:  
        # curves will only get faces when they have a bevel or a extrude            
        if bpy.data.curves[obj.data.name].bevel_depth or bpy.data.curves[obj.data.name].extrude:
            #print(bpy.data.curves[obj.name].bevel_depth , bpy.data.curves[obj.name].extrude)
            return True
        else:
            return False
            
    else:
        if utils.prefs().debug_output:
            print("GoB: unsupported object type:", obj.type)  
        return False
    
    return numFaces


def export_poll(cls, context):  

    # do not allow export if no objects are selected
    if not context.selected_objects:
        return False

    # if one object is selected, check amount of faces. 0 faces will crash zbrush!
    elif len(context.selected_objects) == 1: 
        if context.active_object:
            obj = context.active_object 
            export = check_export_candidates(obj)
        else:
            for obj in context.selected_objects:  
                export = check_export_candidates(obj)
    
    #check for faces in multiple objects, only if any face in object is found exporting should be allowed
    else: 
        exportCandidates=[]
        for obj in context.selected_objects:  
            candidate = check_export_candidates(obj)
            exportCandidates.append(candidate)
        #print("any export candidate: ", any(exportCandidates))
        export = any(exportCandidates)
    
    return export