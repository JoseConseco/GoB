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

import re

import bpy
import bmesh
import mathutils
import time
import math
from bpy.types import Object, Mesh
from . import utils


SCULPT_FACE_SET_ATTRIBUTE = '.sculpt_face_set'
LEGACY_SCULPT_FACE_SET_ATTRIBUTE = 'sculpt_face_set'
SCULPT_FACE_SET_ATTRIBUTE_NAMES = (
    SCULPT_FACE_SET_ATTRIBUTE,
    LEGACY_SCULPT_FACE_SET_ATTRIBUTE,
)


def get_sculpt_face_set_attribute(mesh: Mesh):
    """Return a valid face-set attribute, preferring Blender's native name."""
    for name in SCULPT_FACE_SET_ATTRIBUTE_NAMES:
        attribute = mesh.attributes.get(name)
        if (
            attribute is not None
            and attribute.domain == 'FACE'
            and attribute.data_type == 'INT'
        ):
            return attribute
    return None


def set_sculpt_face_set_attribute(mesh: Mesh, values):
    """Store face-set values under Blender's native attribute name.

    Both the native and legacy undotted names are removed so an export mesh
    cannot contain two competing face-set attributes.
    """
    values = list(values)
    if len(values) != len(mesh.polygons):
        return None

    attribute = mesh.attributes.get(SCULPT_FACE_SET_ATTRIBUTE)
    if attribute is not None and (
        attribute.domain != 'FACE' or attribute.data_type != 'INT'
    ):
        mesh.attributes.remove(attribute)
        mesh.update()
        attribute = None

    legacy_attribute = mesh.attributes.get(LEGACY_SCULPT_FACE_SET_ATTRIBUTE)
    if legacy_attribute is not None:
        mesh.attributes.remove(legacy_attribute)

    if attribute is None:
        attribute = mesh.attributes.new(SCULPT_FACE_SET_ATTRIBUTE, 'INT', 'FACE')
    attribute.data.foreach_set('value', values)
    return attribute


def get_vertex_colors(mesh: Mesh, obj:Object, numVertices):

    if obj.data.color_attributes:
        #fill vcolArray(vert_idx + rgb_offset) = color_xyz
        vcolArray = bytearray([0] * numVertices * 3)
        active_color = obj.data.color_attributes.active_color
        color_attribute = mesh.attributes.get(active_color.name, None)

        # Pre-calculate vertex base indices for faster access
        vertex_indices = [i * 3 for i in range(numVertices)]

        for vert, vertex_index in zip(mesh.vertices, vertex_indices):
            color_data = color_attribute.data[vert.index]
            color = color_data.color_srgb

            vcolArray[vertex_index] = int(255 * color[0])
            vcolArray[vertex_index +1] = int(255 * color[1])
            vcolArray[vertex_index +2] = int(255 * color[2])
    else:
        print('No vertex colors found')

    # Ensure vcolArray is correctly populated
    assert len(vcolArray) == numVertices * 3, "GoB vcolArray length mismatch"

    return vcolArray


_IMPORT_AXIS_MATRIX = mathutils.Matrix(
    (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
)
_EXPORT_AXIS_MATRIX = _IMPORT_AXIS_MATRIX.inverted()
_MIN_SCALE = 1.0e-8


def _positive_finite(value, label):
    """Return a usable positive float, or None after reporting bad input."""

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    if not math.isfinite(value) or value <= _MIN_SCALE:
        print(f"GoB: Invalid {label} {value!r}; using unit scale instead.")
        return None
    return value


def _import_scale_factor() -> float:
    """Return the single scale multiplier used when importing from GoZ."""

    prefs = utils.prefs()
    if prefs.use_scale == "BUNITS":
        unit_scale = _positive_finite(
            bpy.context.scene.unit_settings.scale_length, "Blender unit scale"
        )
        return 1.0 / unit_scale if unit_scale is not None else 1.0

    if prefs.use_scale == "MANUAL":
        manual_scale = _positive_finite(prefs.manual_scale, "manual scale")
        return 1.0 / manual_scale if manual_scale is not None else 1.0

    if prefs.use_scale == "ZUNITS":
        target_scale = _positive_finite(prefs.zbrush_scale, "ZBrush scale")
        obj = bpy.context.active_object
        if obj is None:
            print("GoB: ZBrush Units requires an active object; using unit scale.")
            return 1.0

        max_dimension = _positive_finite(
            max(abs(float(dimension)) for dimension in obj.dimensions),
            "active object dimension",
        )
        if target_scale is None or max_dimension is None:
            return 1.0

        scale = max_dimension / target_scale
        if prefs.debug_output:
            print(
                "GoB ZBrush Units:",
                obj.dimensions,
                "target:",
                target_scale,
                "import scale:",
                scale,
            )
        return scale

    print(f"GoB: Unknown scale mode {prefs.use_scale!r}; using unit scale.")
    return 1.0


def _axis_remap_matrix():
    """Build a validated local-space axis permutation and flip matrix."""

    prefs = utils.prefs()
    axis_names = (
        prefs.remap_x_axis,
        prefs.remap_y_axis,
        prefs.remap_z_axis,
    )
    flip_values = (
        -1.0 if prefs.flip_x_axis else 1.0,
        -1.0 if prefs.flip_y_axis else 1.0,
        -1.0 if prefs.flip_z_axis else 1.0,
    )

    # Preference callbacks normally enforce a permutation. Fall back to the
    # identity mapping if persisted or programmatic values are invalid, while
    # still honoring the explicitly requested axis flips.
    if set(axis_names) != {"X", "Y", "Z"}:
        print(
            f"GoB: Invalid axis remapping {axis_names!r}; "
            "using identity remapping."
        )
        axis_names = ("X", "Y", "Z")

    axis_indices = {"X": 0, "Y": 1, "Z": 2}
    matrix = mathutils.Matrix.Identity(4)
    for row in range(3):
        for column in range(3):
            matrix[row][column] = 0.0
        matrix[row][axis_indices[axis_names[row]]] = flip_values[row]

    return matrix


def apply_transformation(me, is_import=True):
    """Apply reciprocal GoZ axis, unit-scale, remapping, and flip transforms."""

    import_scale = _import_scale_factor()
    remap_matrix = _axis_remap_matrix()

    if is_import:
        # This is the inverse of the export sequence: unit scale is applied
        # exactly once, followed by GoZ axis conversion and local remapping.
        import_matrix = (
            remap_matrix
            @ _IMPORT_AXIS_MATRIX
            @ mathutils.Matrix.Scale(import_scale, 4)
        )
        me.transform(import_matrix)
    else:
        # Remap world-space coordinates, not the temporary mesh around each
        # object's local origin. The exporter applies this returned matrix
        # after obj.matrix_world, preserving relative placement when objects
        # have different origins or unapplied transforms.
        mat_transform = (
            _EXPORT_AXIS_MATRIX
            @ mathutils.Matrix.Scale(1.0 / import_scale, 4)
            @ remap_matrix.inverted()
        )

    # A reflection reverses winding in either direction. Positive unit scales
    # do not affect this determinant, so normals are handled only once here.
    if remap_matrix.determinant() < 0.0:
        me.flip_normals()

    return me, None if is_import else mat_transform


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


def remove_internal_faces(obj:Object):

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


def apply_modifiers(obj:Object) -> Mesh:

    if utils.prefs().performance_profiling:
        print("\\___")
        start_time = utils.profiler(time.perf_counter(), f"Export Profiling: {obj.name}")
        start_total_time = utils.profiler(time.perf_counter(), "")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh depsgraph")

    object_eval = obj.evaluated_get(depsgraph)
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh object_eval")

    original_mesh = obj.data

    if utils.prefs().export_modifiers == 'APPLY_EXPORT':
        mesh_tmp = bpy.data.meshes.new_from_object(object_eval)
        #copy_sculpt_attributes(original_mesh, mesh_tmp)
        obj.data = mesh_tmp
        obj.modifiers.clear()

    elif utils.prefs().export_modifiers == 'ONLY_EXPORT':
        mesh_tmp = object_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if utils.prefs().performance_profiling:
            start_time = utils.profiler(start_time, "Make Mesh to_mesh")

    else:
        mesh_tmp = obj.data

    # Prefer face sets propagated through the evaluated mesh. This preserves
    # their mapping when a modifier changes topology. Fall back to the source
    # mesh only when its polygons still correspond 1:1 with the export mesh.
    face_set_values = None
    face_set_attr = get_sculpt_face_set_attribute(mesh_tmp)
    face_set_source = 'evaluated mesh'
    if face_set_attr is None or len(face_set_attr.data) != len(mesh_tmp.polygons):
        face_set_attr = get_sculpt_face_set_attribute(original_mesh)
        face_set_source = 'source mesh'
        if (
            face_set_attr is not None
            and len(face_set_attr.data) != len(mesh_tmp.polygons)
        ):
            face_set_attr = None

    if utils.prefs().debug_output:
        print(f"Face sets found on {face_set_source}: ", face_set_attr)
    if face_set_attr is not None:
        face_set_values = [d.value for d in face_set_attr.data]

    # Read sculpt mask values from original_mesh — these are per-vertex so
    # triangulation does not affect them, but to_mesh() drops them.
    sculpt_mask_values = None
    mask_attr = original_mesh.attributes.get('.sculpt_mask')
    if mask_attr and len(mask_attr.data) == len(mesh_tmp.vertices):
        sculpt_mask_values = [d.value for d in mask_attr.data]

    #DO the triangulation of Ngons only, but do not write it to original object.
    bm = bmesh.new()
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh bmesh new")

    bm.from_mesh(mesh_tmp)
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh bmesh")

    # Store face set values on a bmesh custom layer so they survive
    # triangulation and join_triangles — bmesh propagates custom face int
    # layers onto new faces created during triangulation automatically.
    face_set_layer = None
    face_set_layer_name = None
    if utils.prefs().debug_output:
        print("Face set values: ", face_set_values)
        print("Face set layer: ", face_set_layer)
    if face_set_values is not None:
        face_set_layer_name = '__gob_face_set_tmp__'
        while bm.faces.layers.int.get(face_set_layer_name) is not None:
            face_set_layer_name += '_'
        face_set_layer = bm.faces.layers.int.new(face_set_layer_name)
        bm.faces.ensure_lookup_table()
        for i, face in enumerate(bm.faces):
            if i < len(face_set_values):
                face[face_set_layer] = face_set_values[i]

    if utils.prefs().debug_output:
        print("Face set layer: ", face_set_layer)

    if facesTotTriangulate := [f for f in bm.faces if len(f.edges) > 4]:
        bmesh.ops.triangulate(bm, faces=facesTotTriangulate)
        if utils.prefs().performance_profiling:
            start_time = utils.profiler(start_time, "Make Mesh triangulate1")

    bm.normal_update(   )

    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh triangulate2")

    mesh_out = bpy.data.meshes.new(name=f'{obj.name}_goz')
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh export_mesh")

    bm.to_mesh(mesh_out)
    mesh_out.validate(verbose=utils.prefs().debug_output)
    mesh_out.update(calc_edges=True, calc_edges_loose=True)

    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh to_mesh")

    bm.free()
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh bm free")

    # Write face set values from the bmesh layer onto mesh_out now that
    # face count is final. We read back via the named attribute that
    # bm.to_mesh() wrote out for us.
    if face_set_layer_name is not None:
        face_set_out = mesh_out.attributes.get(face_set_layer_name)
        if utils.prefs().debug_output:
            print(f"face_set_out is: {face_set_out}")
        if face_set_out is not None:
            src_values = [d.value for d in face_set_out.data]
            sculpt_fs = set_sculpt_face_set_attribute(mesh_out, src_values)
            if sculpt_fs is not None:
                mesh_out.attributes.remove(face_set_out)
            if utils.prefs().debug_output:
                print("Attributes:", mesh_out.attributes.keys())
                if get_sculpt_face_set_attribute(mesh_out):
                    print("true")
                else:
                    print("false")

    # Restore sculpt mask — per-vertex so unaffected by triangulation,
    # but still needs explicit copy as bmesh drops it.
    if sculpt_mask_values is not None:
        sculpt_mask = mesh_out.attributes.get('.sculpt_mask')
        if sculpt_mask:
            mesh_out.attributes.remove(sculpt_mask)
        sculpt_mask = mesh_out.attributes.new('.sculpt_mask', 'FLOAT', 'POINT')
        for i, d in enumerate(sculpt_mask.data):
            if i < len(sculpt_mask_values):
                d.value = sculpt_mask_values[i]

    obj.to_mesh_clear()
    if utils.prefs().performance_profiling:
        start_time = utils.profiler(start_time, "Make Mesh to_mesh_clear")

    if utils.prefs().performance_profiling:
        utils.profiler(start_total_time, "Make Mesh return\n _____/")

    return mesh_out


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
    obj_clone = bpy.data.objects.new(f'{obj.name}_{obj.type}', mesh_clone)
    if link:
        bpy.context.view_layer.active_layer_collection.collection.objects.link(obj_clone)

    return obj_clone


def check_export_candidates(obj):

    if obj.type in {'MESH'}:
        if utils.prefs().export_modifiers in {'IGNORE'}:
            # if export modifers is Ignored check for polygons to identify export candidates
            numFaces = len(obj.data.polygons)
            #print("numfaces 3 no active modifiers: ", numFaces)

        elif obj.modifiers:
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

    elif obj.type in {'SURFACE', 'FONT', 'META'}:
        #allow export for non mesh type objects
        return True

    elif obj.type in {'CURVE'}:
        # curves will only get faces when they have a bevel or a extrude
        return bool(
            bpy.data.curves[obj.data.name].bevel_depth
            or bpy.data.curves[obj.data.name].extrude
        )
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
