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

import os
import random
import string
import time
from struct import unpack, unpack_from

import bmesh
import bpy
import mathutils
import numpy as np
from bpy.props import EnumProperty
from bpy.types import Operator

from . import geometry, nodes, paths, utils

run_background_update = False
gob_import_cache = []
cached_last_edition_time = time.perf_counter()
start_time = None


def _report_import_warning(operator, message):
    """Show recoverable GoZ import problems in Blender and the console."""

    message = f"GoB: {message}"
    print(message)
    try:
        operator.report({"WARNING"}, message)
    except (AttributeError, RuntimeError):
        # Imports can also be triggered by the background timer, where an
        # operator report may not have a valid UI destination.
        pass


def _read_goz_section(goz_file, operator, section_name):
    """Read one GoZ section without allowing it to consume the next tag.

    The section tag has already been read by the caller. GoZ's stored section
    length includes that four-byte tag, the four-byte length, and the
    eight-byte element count, leaving ``length - 16`` payload bytes.
    """

    header = goz_file.read(12)
    if len(header) != 12:
        _report_import_warning(
            operator,
            f"{section_name} section has a truncated header; the section was ignored.",
        )
        return 0, b""

    section_length = unpack_from("<I", header, 0)[0]
    element_count = unpack_from("<Q", header, 4)[0]
    if section_length < 16:
        _report_import_warning(
            operator,
            f"{section_name} section has an invalid length ({section_length}); "
            "the section was ignored.",
        )
        return element_count, b""

    payload_length = section_length - 16
    payload_start = goz_file.tell()
    goz_file.seek(0, 2)
    available_bytes = max(0, goz_file.tell() - payload_start)
    goz_file.seek(payload_start, 0)
    payload = goz_file.read(min(payload_length, available_bytes))
    if len(payload) != payload_length:
        _report_import_warning(
            operator,
            f"{section_name} section is truncated: expected {payload_length} "
            f"payload bytes, found {len(payload)}.",
        )

    return element_count, payload


def _decode_face_data(faces_data):
    """Return loop starts, loop totals, and loop vertex indices."""

    if isinstance(faces_data, np.ndarray) and (
        faces_data.ndim == 2 and faces_data.shape[1] == 4
    ):
        records = np.asarray(faces_data, dtype=np.uint32)
        face_count = len(records)
        triangles = records[:, 3] == np.uint32(0xFFFFFFFF)
        legacy_zero = records[:, 3] == 0
        loop_totals = np.where(triangles, 3, 4).astype(np.int32)
        loop_starts = np.empty(face_count, dtype=np.int32)
        if face_count:
            loop_starts[0] = 0
            np.cumsum(
                loop_totals[:-1], dtype=np.int64, out=loop_starts[1:]
            )

        loop_vertices = np.empty(
            int(loop_totals.sum(dtype=np.int64)), dtype=np.int32
        )
        rows = np.arange(face_count)
        for corner in range(4):
            valid = loop_totals > corner
            source_corner = np.full(face_count, corner, dtype=np.int8)
            if corner == 0:
                source_corner[legacy_zero] = 3
            else:
                source_corner[legacy_zero] = corner - 1
            loop_vertices[loop_starts[valid] + corner] = records[
                rows[valid], source_corner[valid]
            ].astype(np.int32, copy=False)
        return loop_starts, loop_totals, loop_vertices

    loop_totals = np.fromiter(
        (len(face) for face in faces_data),
        dtype=np.int32,
        count=len(faces_data),
    )
    loop_starts = np.empty(len(loop_totals), dtype=np.int32)
    if len(loop_totals):
        loop_starts[0] = 0
        np.cumsum(loop_totals[:-1], dtype=np.int64, out=loop_starts[1:])
    loop_vertices = np.fromiter(
        (int(vertex) for face in faces_data for vertex in face),
        dtype=np.int32,
        count=int(loop_totals.sum(dtype=np.int64)),
    )
    return loop_starts, loop_totals, loop_vertices


class GoB_OT_import(Operator):
    bl_idname = "scene.gob_import"
    bl_label = "Import from GOZ"
    bl_description = "GoZ Import. Activate to enable Import from GoZ"

    action: EnumProperty(
        items=[
            ("MANUAL", "manual import", "manual import"),
            ("AUTO", "toggle automatic import", "toggle automatic import"),
        ]
    )

    @staticmethod
    def mesh_topology_matches(
        me, vertsData, facesData, decoded_faces=None
    ) -> bool:
        """Return whether imported geometry uses the mesh's existing indices."""

        if len(me.vertices) != len(vertsData) or len(me.polygons) != len(facesData):
            return False

        # GoZ does not carry loose edges. Keeping one would make this an
        # inexact topology match even if all imported faces compare equal.
        loose_edges = np.empty(len(me.edges), dtype=np.bool_)
        me.edges.foreach_get("is_loose", loose_edges)
        if np.any(loose_edges):
            return False

        if decoded_faces is None:
            decoded_faces = _decode_face_data(facesData)
        _, imported_loop_totals, imported_loop_vertices = decoded_faces
        if len(me.loops) != len(imported_loop_vertices):
            return False

        mesh_loop_totals = np.empty(len(me.polygons), dtype=np.int32)
        mesh_loop_vertices = np.empty(len(me.loops), dtype=np.int32)
        me.polygons.foreach_get("loop_total", mesh_loop_totals)
        me.loops.foreach_get("vertex_index", mesh_loop_vertices)
        return bool(
            np.array_equal(mesh_loop_totals, imported_loop_totals)
            and np.array_equal(mesh_loop_vertices, imported_loop_vertices)
        )

    def make_mesh(self, objName, vertsData, facesData) -> tuple:
        """Create or update a mesh object from the given vertices and faces data.

        Args:
            objName (str): The name of the object to create or update.
            vertsData (list of tuple): A list of vertex coordinates, where each vertex is represented as a tuple of three floats (x, y, z).
            facesData (list of tuple): A list of face definitions, where each face is represented as a tuple of vertex indices.

        Returns:
            tuple: A tuple containing the created or updated object (bpy.types.Object) and its mesh data (bpy.types.Mesh).
        """

        if utils.prefs().debug_output:
            print(f"\nGoB Object Name: {objName}")

        obj = bpy.data.objects.get(objName)
        object_exists = obj is not None
        if object_exists:
            if utils.prefs().debug_output:
                print(f"\nGoB Object already exists: {objName}")
            me = obj.data
        else:
            if utils.prefs().debug_output:
                print(f"\nGoB Creating new object: {objName}")
            me = bpy.data.meshes.new(objName)
            obj = bpy.data.objects.new(objName, me)
            if bpy.context.view_layer.active_layer_collection:
                bpy.context.view_layer.active_layer_collection.collection.objects.link(
                    obj
                )
            else:
                print(
                    "Error: Active layer collection is not set or invalid. Object could not be linked."
                )

        decoded_faces = _decode_face_data(facesData)
        topology_matches = object_exists and self.mesh_topology_matches(
            me, vertsData, facesData, decoded_faces
        )

        if topology_matches:
            # Keep the existing vertices so Blender's per-vertex deform data
            # (including rigging vertex groups) remains attached to the same
            # indices. Exact face matching ensures changed connectivity still
            # takes the full rebuild path introduced in GoB 4.1.8.
            coordinates = np.asarray(vertsData, dtype=np.float32).reshape(-1)
            me.vertices.foreach_set("co", coordinates)
        else:
            # Rebuild whenever topology differs. Preserving weights by index in
            # this case could silently attach them to different vertices.
            if bpy.app.version >= (3, 6, 0):
                me.clear_geometry()
            else:
                me.vertices.clear()
                me.edges.clear()
                me.polygons.clear()

            loop_starts, loop_totals, loop_vertices = decoded_faces
            me.vertices.add(len(vertsData))
            me.vertices.foreach_set(
                "co", np.asarray(vertsData, dtype=np.float32).reshape(-1)
            )
            me.loops.add(len(loop_vertices))
            me.loops.foreach_set("vertex_index", loop_vertices)
            me.polygons.add(len(loop_totals))
            me.polygons.foreach_set("loop_start", loop_starts)
            me.polygons.foreach_set("loop_total", loop_totals)
        me.update(calc_edges=True, calc_edges_loose=True)

        # Apply transformations and validate mesh
        me, _ = geometry.apply_transformation(me, is_import=True)
        me.transform(obj.matrix_world.inverted())
        me.validate(verbose=utils.prefs().debug_output)

        # Set object as active and update view layer
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()

        return obj, me

    def GoZit(self, pathFile):
        if utils.prefs().performance_profiling:
            print("\n")
            start_time = utils.profiler(time.perf_counter(), "Start Object Profiling")
            start_total_time = utils.profiler(time.perf_counter(), "...")

        unknown_tag = 0
        vertsData = np.empty((0, 3), dtype=np.float32)
        facesData = np.empty((0, 4), dtype=np.uint32)
        subdiv = 0
        objMat = None
        diff_texture, disp_texture, norm_texture = None, None, None
        exists = os.path.isfile(pathFile)
        if not exists:
            if utils.prefs().debug_output:
                print(f"Cant read mesh from: {pathFile}. Skipping")
            return

        with open(pathFile, "rb") as goz_file:
            goz_file.seek(36, 0)
            lenObjName = unpack("<I", goz_file.read(4))[0] - 16
            goz_file.seek(8, 1)
            obj_name = unpack("%ss" % lenObjName, goz_file.read(lenObjName))[0]
            # remove non ascii chars eg. /x 00
            objName = "".join(
                [
                    letter
                    for letter in obj_name[8:].decode("utf-8")
                    if letter in string.printable
                ]
            )

            if utils.prefs().debug_output:
                print(f"\n\nGoB Importing: \n{pathFile, objName}")
            if utils.prefs().performance_profiling:
                print(f"GoB Importing: {objName}")
            tag = goz_file.read(4)

            while tag:
                # Name
                if tag == b"\x89\x13\x00\x00":
                    if utils.prefs().debug_output:
                        print("_ Name:", tag)
                    cnt = unpack("<L", goz_file.read(4))[0] - 8
                    goz_file.seek(cnt, 1)
                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(start_time, "____Unpack Mesh Name")

                # Subdivision Levels
                elif tag == b"\x8a\x13\x00\x00":
                    goz_file.seek(4, 1)
                    cnt = unpack("<Q", goz_file.read(8))[0]
                    if utils.prefs().debug_output:
                        print("_ Subdivision Level 8a13 cnt: ", cnt)
                        print("_ Subdivision Level 8a13:", tag)
                    for i in range(cnt):
                        subdiv = unpack("<I", goz_file.read(4))[0]
                        v2 = unpack("<I", goz_file.read(4))[0]
                        v3 = unpack("<I", goz_file.read(4))[0]
                        v4 = unpack("<I", goz_file.read(4))[0]
                        print("_ _ Subdivision Level 8a13: ", subdiv, v2, v3, v4)

                # Vertices
                elif tag == b"\x11\x27\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ Vertices:", tag)
                    cnt, vertex_payload = _read_goz_section(
                        goz_file, self, "Vertex"
                    )
                    record_size = 3 * 4
                    payload_vertex_count = len(vertex_payload) // record_size
                    trailing_byte_count = len(vertex_payload) % record_size
                    import_vertex_count = min(cnt, payload_vertex_count)
                    if payload_vertex_count != cnt or trailing_byte_count:
                        _report_import_warning(
                            self,
                            "Vertex data is partial or inconsistent: "
                            f"the section declares {cnt} vertices and its payload "
                            f"contains {payload_vertex_count} complete records; "
                            f"importing {import_vertex_count} vertices.",
                        )

                    imported_vertices = np.frombuffer(
                        vertex_payload,
                        dtype="<f4",
                        count=import_vertex_count * 3,
                    ).reshape((-1, 3))
                    if len(vertsData):
                        vertsData = np.concatenate((vertsData, imported_vertices))
                    else:
                        vertsData = imported_vertices

                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(
                            start_time, "____Unpack Mesh Vertices"
                        )

                # Faces
                elif tag == b"\x21\x4e\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ Faces:", tag)
                    cnt, face_payload = _read_goz_section(goz_file, self, "Face")
                    record_size = 4 * 4
                    payload_face_count = len(face_payload) // record_size
                    trailing_byte_count = len(face_payload) % record_size
                    import_face_count = min(cnt, payload_face_count)
                    if payload_face_count != cnt or trailing_byte_count:
                        _report_import_warning(
                            self,
                            "Face data is partial or inconsistent: "
                            f"the section declares {cnt} faces and its payload "
                            f"contains {payload_face_count} complete records; "
                            f"importing {import_face_count} faces.",
                        )

                    face_records = np.frombuffer(
                        face_payload,
                        dtype="<u4",
                        count=import_face_count * 4,
                    ).reshape((-1, 4))
                    if len(facesData):
                        facesData = np.concatenate((facesData, face_records))
                    else:
                        facesData = face_records
                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(start_time, "____Unpack Mesh Faces")

                # UVs
                elif tag == b"\xa9\x61\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ UVs:", tag)
                    break
                # Polypainting
                elif tag == b"\xb9\x88\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ Polypainting:", tag)
                    break
                # Mask
                elif tag == b"\x32\x75\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ Mask:", tag)
                    break
                # Polygroups
                elif tag == b"\x41\x9c\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ Polyroups:", tag)
                    break
                # End
                elif tag == b"\x00\x00\x00\x00":
                    if utils.prefs().debug_output:
                        print("__ End:", tag)
                    break
                # Unknown tags
                else:
                    if utils.prefs().debug_output:
                        print("____ Unknown tag:{0}".format(tag))
                    if unknown_tag >= 10:
                        if utils.prefs().debug_output:
                            print("...Too many mesh tags unknown...\n")
                        unknown_tag += 1
                        cnt = unpack("<I", goz_file.read(4))[0] - 8
                        goz_file.seek(cnt, 1)
                        break

                tag = goz_file.read(4)

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Unpack Mesh Data\n")

            obj, me = self.make_mesh(objName, vertsData, facesData)
            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Make Mesh \n")

            unknown_tag = 0

            while tag:
                # UVs
                if tag == b"\xa9\x61\x00\x00":
                    if utils.prefs().debug_output:
                        print("Import UV: ", utils.prefs().import_uv)

                    cnt, uv_payload = _read_goz_section(goz_file, self, "UV")

                    if utils.prefs().import_uv:
                        uv_record_size = 4 * 2 * 4
                        payload_face_count = len(uv_payload) // uv_record_size
                        trailing_byte_count = len(uv_payload) % uv_record_size
                        import_face_count = min(
                            cnt, payload_face_count, len(me.polygons)
                        )

                        if (
                            cnt != len(me.polygons)
                            or payload_face_count != cnt
                            or trailing_byte_count
                        ):
                            trailing_note = (
                                f"; ignored {trailing_byte_count} trailing bytes"
                                if trailing_byte_count
                                else ""
                            )
                            _report_import_warning(
                                self,
                                "UV data is partial or inconsistent: "
                                f"mesh has {len(me.polygons)} faces, the section "
                                f"declares {cnt}, and its payload contains "
                                f"{payload_face_count} complete face records. "
                                f"Imported UVs for the first {import_face_count} faces"
                                f"{trailing_note}.",
                            )

                        uv_layer = me.uv_layers.get(utils.prefs().import_uv_name)
                        uv_layer_is_new = uv_layer is None
                        if uv_layer is None:
                            uv_layer = me.uv_layers.new(
                                name=utils.prefs().import_uv_name
                            )

                        uv_records = np.frombuffer(
                            uv_payload,
                            dtype="<f4",
                            count=payload_face_count * 8,
                        ).reshape((-1, 4, 2))[:import_face_count].copy()
                        if utils.prefs().import_uv_flip_x:
                            uv_records[:, :, 0] = 1.0 - uv_records[:, :, 0]
                        if utils.prefs().import_uv_flip_y:
                            uv_records[:, :, 1] = 1.0 - uv_records[:, :, 1]

                        polygon_count = len(me.polygons)
                        loop_starts = np.empty(polygon_count, dtype=np.int32)
                        loop_totals = np.empty(polygon_count, dtype=np.int32)
                        me.polygons.foreach_get("loop_start", loop_starts)
                        me.polygons.foreach_get("loop_total", loop_totals)

                        imported_loop_totals = loop_totals[:import_face_count]
                        if np.any(imported_loop_totals > 4):
                            _report_import_warning(
                                self,
                                "UV data contains four corners per face; only the "
                                "first four corners of an n-gon can be imported.",
                            )

                        corners = np.arange(4, dtype=np.int32)
                        valid_corners = (
                            corners[None, :] < imported_loop_totals[:, None]
                        )
                        mesh_loop_indices = (
                            loop_starts[:import_face_count, None] + corners[None, :]
                        )[valid_corners]
                        imported_uvs = uv_records[valid_corners]

                        loop_uvs = np.zeros(
                            len(uv_layer.data) * 2, dtype=np.float32
                        )
                        if not uv_layer_is_new:
                            uv_layer.data.foreach_get("uv", loop_uvs)
                        loop_uvs = loop_uvs.reshape((-1, 2))
                        loop_uvs[mesh_loop_indices] = imported_uvs
                        uv_layer.data.foreach_set("uv", loop_uvs.reshape(-1))
                        me.update(calc_edges=True, calc_edges_loose=True)

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(start_time, "UV Map")

                # Polypainting
                elif tag == b"\xb9\x88\x00\x00":
                    if utils.prefs().debug_output:
                        print("Import Polypaint: ", utils.prefs().import_polypaint)

                    cnt, polypaint_payload = _read_goz_section(
                        goz_file, self, "Polypaint"
                    )

                    if utils.prefs().import_polypaint:
                        payload_vertex_count = len(polypaint_payload) // 4
                        trailing_byte_count = len(polypaint_payload) % 4
                        import_vertex_count = min(
                            cnt, payload_vertex_count, len(me.vertices)
                        )
                        if (
                            cnt != len(me.vertices)
                            or payload_vertex_count != cnt
                            or trailing_byte_count
                        ):
                            trailing_note = (
                                f"; ignored {trailing_byte_count} trailing bytes"
                                if trailing_byte_count
                                else ""
                            )
                            _report_import_warning(
                                self,
                                "Polypaint data is partial or inconsistent: "
                                f"mesh has {len(me.vertices)} vertices, the section "
                                f"declares {cnt}, and its payload contains "
                                f"{payload_vertex_count} complete color records. "
                                f"Imported colors for the first {import_vertex_count} "
                                f"vertices{trailing_note}.",
                            )

                        color_records = np.frombuffer(
                            polypaint_payload,
                            dtype=np.uint8,
                            count=payload_vertex_count * 4,
                        ).reshape((-1, 4))[:import_vertex_count]
                        polypaint_colors = np.ones(
                            (import_vertex_count, 4), dtype=np.float32
                        )
                        polypaint_colors[:, :3] = (
                            color_records[:, 2::-1].astype(np.float32) / 255.0
                        )

                        # Assign colors
                        if import_vertex_count:
                            if bpy.app.version < (3, 4, 0):
                                polypaintData = polypaint_colors.tolist()
                                bm = bmesh.new()
                                bm.from_mesh(me)
                                bm.faces.ensure_lookup_table()
                                if me.vertex_colors:
                                    if (
                                        utils.prefs().import_polypaint_name
                                        in me.vertex_colors
                                    ):
                                        color_layer = bm.loops.layers.color.get(
                                            utils.prefs().import_polypaint_name
                                        )
                                    else:
                                        color_layer = bm.loops.layers.color.new(
                                            utils.prefs().import_polypaint_name
                                        )
                                else:
                                    color_layer = bm.loops.layers.color.new(
                                        utils.prefs().import_polypaint_name
                                    )

                                for face in bm.faces:
                                    for loop in face.loops:
                                        if loop.vert.index < len(polypaintData):
                                            loop[color_layer] = polypaintData[
                                                loop.vert.index
                                            ]

                                bm.to_mesh(me)
                                bm.free()
                                me.update(calc_edges=True, calc_edges_loose=True)
                            else:
                                color_attribute = me.color_attributes.get(
                                    utils.prefs().import_polypaint_name
                                )
                                if (
                                    color_attribute is not None
                                    and color_attribute.domain != "POINT"
                                ):
                                    me.color_attributes.remove(color_attribute)
                                    color_attribute = None
                                if color_attribute is None:
                                    color_attribute = me.color_attributes.new(
                                        utils.prefs().import_polypaint_name,
                                        "BYTE_COLOR",
                                        "POINT",
                                    )

                                color_values = np.empty(
                                    len(color_attribute.data) * 4,
                                    dtype=np.float32,
                                )
                                color_attribute.data.foreach_get(
                                    "color_srgb", color_values
                                )
                                color_values = color_values.reshape((-1, 4))
                                color_values[:import_vertex_count] = polypaint_colors
                                color_attribute.data.foreach_set(
                                    "color_srgb", color_values.reshape(-1)
                                )

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(start_time, "Polypaint Assign")

                # Mask
                elif tag == b"\x32\x75\x00\x00":
                    if utils.prefs().debug_output:
                        print("Import Mask: ", utils.prefs().import_mask)

                    cnt, mask_payload = _read_goz_section(goz_file, self, "Mask")

                    if utils.prefs().import_mask:
                        payload_vertex_count = len(mask_payload) // 2
                        trailing_byte_count = len(mask_payload) % 2
                        import_vertex_count = min(
                            cnt, payload_vertex_count, len(me.vertices)
                        )
                        if (
                            cnt != len(me.vertices)
                            or payload_vertex_count != cnt
                            or trailing_byte_count
                        ):
                            _report_import_warning(
                                self,
                                "Mask data is partial or inconsistent: "
                                f"mesh has {len(me.vertices)} vertices, the section "
                                f"declares {cnt}, and its payload contains "
                                f"{payload_vertex_count} complete mask records. "
                                f"Imported masks for the first {import_vertex_count} "
                                "vertices.",
                            )

                        mask_records = np.frombuffer(
                            mask_payload,
                            dtype="<u2",
                            count=payload_vertex_count,
                        )[:import_vertex_count]
                        mask_weights = mask_records.astype(np.float32) / 65535.0

                        # Create or clear vertex group for mask
                        if "mask" in obj.vertex_groups:
                            obj.vertex_groups.remove(obj.vertex_groups["mask"])
                        groupMask = obj.vertex_groups.new(name="mask")

                        # Blender accepts one weight per add() call. Group equal
                        # weights so common mask values are assigned in batches.
                        weighted_indices = np.flatnonzero(mask_records < 65535)
                        if len(weighted_indices):
                            weight_order = np.argsort(
                                mask_records[weighted_indices], kind="stable"
                            )
                            weighted_indices = weighted_indices[weight_order]
                            sorted_weights = mask_records[weighted_indices]
                            weight_boundaries = (
                                np.flatnonzero(
                                    sorted_weights[1:] != sorted_weights[:-1]
                                )
                                + 1
                            )
                            for vertex_indices in np.split(
                                weighted_indices, weight_boundaries
                            ):
                                raw_weight = int(mask_records[vertex_indices[0]])
                                groupMask.add(
                                    vertex_indices.tolist(),
                                    raw_weight / 65535.0,
                                    "REPLACE",
                                )

                        # Create sculpt mask attribute (available in Blender 4.1+)
                        if hasattr(me, "attributes"):
                            mask_attr = me.attributes.get(".sculpt_mask")
                            if mask_attr is not None and (
                                mask_attr.domain != "POINT"
                                or mask_attr.data_type != "FLOAT"
                            ):
                                me.attributes.remove(mask_attr)
                                mask_attr = None
                            if mask_attr is None:
                                mask_attr = me.attributes.new(
                                    ".sculpt_mask", "FLOAT", "POINT"
                                )
                            mask_values = np.empty(
                                len(mask_attr.data), dtype=np.float32
                            )
                            mask_attr.data.foreach_get("value", mask_values)
                            mask_values[:import_vertex_count] = 1.0 - mask_weights
                            mask_attr.data.foreach_set("value", mask_values)

                            if utils.prefs().debug_output:
                                print("Sculpt mask attribute created and populated")

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(start_time, "Mask\n")

                # Polygroups
                elif tag == b"\x41\x9c\x00\x00":
                    if utils.prefs().debug_output:
                        print("Polygroups:", tag)
                        print(
                            "Import Polygroups to Vertex Groups:",
                            utils.prefs().import_polygroups_to_vertexgroups,
                        )
                        print(
                            "Import Polygroups to Face Sets:",
                            utils.prefs().import_polygroups_to_facesets,
                        )

                    cnt, polygroup_payload = _read_goz_section(
                        goz_file, self, "Polygroup"
                    )
                    payload_face_count = len(polygroup_payload) // 2
                    trailing_byte_count = len(polygroup_payload) % 2
                    import_face_count = min(
                        cnt, payload_face_count, len(me.polygons)
                    )
                    import_polygroups = (
                        utils.prefs().import_material == "POLYGROUPS"
                        or utils.prefs().import_polygroups_to_facesets
                        or utils.prefs().import_polygroups_to_vertexgroups
                    )
                    if import_polygroups and (
                        cnt != len(me.polygons)
                        or payload_face_count != cnt
                        or trailing_byte_count
                    ):
                        _report_import_warning(
                            self,
                            "Polygroup data is partial or inconsistent: "
                            f"mesh has {len(me.polygons)} faces, the section "
                            f"declares {cnt}, and its payload contains "
                            f"{payload_face_count} complete polygroup records. "
                            f"Imported polygroups for the first {import_face_count} "
                            "faces.",
                        )

                    if not import_polygroups:
                        tag = goz_file.read(4)
                        continue

                    polyGroupData = np.frombuffer(
                        polygroup_payload,
                        dtype="<u2",
                        count=payload_face_count,
                    )[:import_face_count]
                    unique_polygroup_values, polygroup_inverse = np.unique(
                        polyGroupData, return_inverse=True
                    )
                    unique_polygroups = [
                        int(group) for group in unique_polygroup_values
                    ]

                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(start_time, "Create polyGroupData")

                    # Import polygroups to materials
                    if utils.prefs().import_material == "POLYGROUPS":
                        material_slot_indices = {}
                        for pgmat in unique_polygroups:
                            objMat = bpy.data.materials.get(
                                str(pgmat)
                            ) or bpy.data.materials.new(str(pgmat))
                            # assign material to object
                            nodes.create_base_nodes(objMat)
                            if objMat.name not in obj.material_slots:
                                obj.data.materials.append(objMat)
                                objMat.use_nodes = True
                                rgba = (
                                    random.random(),
                                    random.random(),
                                    random.random(),
                                    1,
                                )
                                objMat.diffuse_color = rgba
                                objMat.node_tree.nodes["Principled BSDF"].inputs[
                                    0
                                ].default_value = rgba
                            material_slot_indices[pgmat] = obj.material_slots[
                                str(pgmat)
                            ].slot_index

                        material_indices = np.empty(
                            len(me.polygons), dtype=np.int32
                        )
                        me.polygons.foreach_get("material_index", material_indices)
                        slot_lookup = np.asarray(
                            [
                                material_slot_indices[int(group)]
                                for group in unique_polygroup_values
                            ],
                            dtype=np.int32,
                        )
                        material_indices[:import_face_count] = slot_lookup[
                            polygroup_inverse
                        ]
                        me.polygons.foreach_set("material_index", material_indices)

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(
                                start_time, "Import materials POLYGROUPS"
                            )

                    # Import polygroups to vertex groups
                    if utils.prefs().import_polygroups_to_vertexgroups:
                        vertex_groups = {}
                        for group in unique_polygroups:
                            group_name = str(group)
                            existing_group = obj.vertex_groups.get(group_name)
                            if existing_group is not None:
                                obj.vertex_groups.remove(existing_group)
                            vertex_groups[group] = obj.vertex_groups.new(
                                name=group_name
                            )

                        if import_face_count:
                            polygon_count = len(me.polygons)
                            loop_starts = np.empty(
                                polygon_count, dtype=np.int32
                            )
                            loop_totals = np.empty(
                                polygon_count, dtype=np.int32
                            )
                            loop_vertices = np.empty(
                                len(me.loops), dtype=np.int32
                            )
                            me.polygons.foreach_get(
                                "loop_start", loop_starts
                            )
                            me.polygons.foreach_get(
                                "loop_total", loop_totals
                            )
                            me.loops.foreach_get(
                                "vertex_index", loop_vertices
                            )

                            imported_totals = loop_totals[:import_face_count]
                            local_starts = np.empty(
                                import_face_count, dtype=np.int64
                            )
                            local_starts[0] = 0
                            if import_face_count > 1:
                                np.cumsum(
                                    imported_totals[:-1],
                                    dtype=np.int64,
                                    out=local_starts[1:],
                                )
                            imported_loop_count = int(
                                imported_totals.sum(dtype=np.int64)
                            )
                            local_positions = np.arange(
                                imported_loop_count, dtype=np.int64
                            ) - np.repeat(local_starts, imported_totals)
                            mesh_loop_indices = np.repeat(
                                loop_starts[:import_face_count], imported_totals
                            ) + local_positions
                            grouped_vertices = loop_vertices[mesh_loop_indices]
                            grouped_polygroups = np.repeat(
                                polyGroupData, imported_totals
                            )

                            order = np.lexsort(
                                (grouped_vertices, grouped_polygroups)
                            )
                            sorted_groups = grouped_polygroups[order]
                            sorted_vertices = grouped_vertices[order]
                            keep = np.ones(len(order), dtype=np.bool_)
                            keep[1:] = (
                                sorted_groups[1:] != sorted_groups[:-1]
                            ) | (
                                sorted_vertices[1:] != sorted_vertices[:-1]
                            )
                            sorted_groups = sorted_groups[keep]
                            sorted_vertices = sorted_vertices[keep]
                            boundaries = np.flatnonzero(
                                np.r_[
                                    True,
                                    sorted_groups[1:] != sorted_groups[:-1],
                                    True,
                                ]
                            )
                            for start, end in zip(
                                boundaries[:-1], boundaries[1:]
                            ):
                                group = int(sorted_groups[start])
                                vertex_groups[group].add(
                                    sorted_vertices[start:end].tolist(),
                                    1.0,
                                    "REPLACE",
                                )

                        if utils.prefs().performance_profiling:
                            start_time = utils.profiler(
                                start_time, "Import polygroups to vertex groups"
                            )

                    # Import polygroups to face sets
                    if utils.prefs().import_polygroups_to_facesets:
                        face_set_index_storage = np.zeros(
                            len(me.polygons), dtype=np.int32
                        )
                        face_set_index_storage[:import_face_count] = polyGroupData

                    # Apply face sets
                    if utils.prefs().import_polygroups_to_facesets:
                        geometry.set_sculpt_face_set_attribute(
                            obj.data, face_set_index_storage
                        )

                    if utils.prefs().performance_profiling:
                        start_time = utils.profiler(
                            start_time, "Assign data to polygons"
                        )

                # End
                elif tag == b"\x00\x00\x00\x00":
                    print("End:", tag)
                    break

                # Diffuse Texture
                elif tag == b"\xc9\xaf\x00\x00":
                    if utils.prefs().debug_output:
                        print("Diff map:", tag)
                    texture_name = obj.name + utils.prefs().import_diffuse_suffix
                    cnt = unpack("<I", goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    diffName = unpack("%ss" % cnt, goz_file.read(cnt))[0]
                    if utils.prefs().debug_output:
                        print(diffName.decode("utf-8"))
                    img = bpy.data.images.load(
                        diffName.strip().decode("utf-8"), check_existing=True
                    )
                    img.name = texture_name
                    img.reload()

                    if not texture_name in bpy.data.textures:
                        txtDiff = bpy.data.textures.new(texture_name, "IMAGE")
                        txtDiff.image = img
                    diff_texture = img

                # Displacement Texture
                elif tag == b"\xd9\xd6\x00\x00":
                    if utils.prefs().debug_output:
                        print("Disp map:", tag)
                    texture_name = obj.name + utils.prefs().import_displace_suffix
                    cnt = unpack("<I", goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    dispName = unpack("%ss" % cnt, goz_file.read(cnt))[0]
                    if utils.prefs().debug_output:
                        print(dispName.decode("utf-8"))
                    img = bpy.data.images.load(
                        dispName.strip().decode("utf-8"), check_existing=True
                    )
                    img.name = texture_name
                    img.reload()

                    if not texture_name in bpy.data.textures:
                        txtDisp = bpy.data.textures.new(texture_name, "IMAGE")
                        txtDisp.image = img
                    disp_texture = img

                # Normal Map Texture
                elif tag == b"\x51\xc3\x00\x00":
                    if utils.prefs().debug_output:
                        print("Normal map:", tag)
                    texture_name = obj.name + utils.prefs().import_normal_suffix
                    cnt = unpack("<I", goz_file.read(4))[0] - 16
                    goz_file.seek(8, 1)
                    normName = unpack("%ss" % cnt, goz_file.read(cnt))[0]
                    if utils.prefs().debug_output:
                        print(normName.decode("utf-8"))
                    img = bpy.data.images.load(
                        normName.strip().decode("utf-8"), check_existing=True
                    )
                    img.name = texture_name
                    img.reload()

                    if not texture_name in bpy.data.textures:
                        txtNorm = bpy.data.textures.new(texture_name, "IMAGE")
                        txtNorm.image = img
                    norm_texture = img

                # Unknown tags
                else:
                    if utils.prefs().debug_output:
                        print("____ Unknown tag:{0}".format(tag))
                    if unknown_tag >= 10:
                        if utils.prefs().debug_output:
                            print("...Too many object tags unknown...\n")
                        unknown_tag += 1
                        cnt = unpack("<I", goz_file.read(4))[0] - 8
                        goz_file.seek(cnt, 1)
                        break

                tag = goz_file.read(4)

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Textures")

            # MATERIALS
            if utils.prefs().import_material:
                if utils.prefs().debug_output:
                    print("Import Material: ", utils.prefs().import_material)

                # POLYPAINT
                if utils.prefs().import_material == "POLYPAINT":
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

                        nodes.materail_from_polypaint(objMat)

                # TEXTURES
                elif utils.prefs().import_material == "TEXTURES":
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
                    nodes.material_fromm_texture(
                        objMat, diff_texture, norm_texture, disp_texture
                    )

            if utils.prefs().performance_profiling:
                start_time = utils.profiler(start_time, "Material Node")

            if utils.prefs().performance_profiling:
                print(30 * "-")
                utils.profiler(start_total_time, "Object Import Time")
                print(30 * "-")
        return

    def execute(self, context):

        if utils.prefs().custom_pixologoc_path:
            paths.PATH_GOZ = utils.prefs().pixologoc_path

        global gob_import_cache
        goz_obj_paths = []
        try:
            with open(
                os.path.join(paths.PATH_GOZ, "GoZBrush", "GoZ_ObjectList.txt"), "rt"
            ) as goz_objs_list:
                goz_obj_paths.extend(f"{line.strip()}.GoZ" for line in goz_objs_list)
        except PermissionError:
            if utils.prefs().debug_output:
                print("GoB: GoZ_ObjectList already in use! Try again Later")
        except Exception as e:
            print(e)

        # Goz wipes this file before each export so it can be used to reset the import cache
        if not goz_obj_paths:
            if utils.prefs().debug_output:
                self.report({"INFO"}, message="GoB: No goz files in GoZ_ObjectList")
            return {"CANCELLED"}

        currentContext = None
        if context.object:
            currentContext = context.object.mode
            if context.object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

        if utils.prefs().performance_profiling:
            print("\n", 100 * "=")
            start_time = utils.profiler(
                time.perf_counter(), "GoB: Start Import Profiling"
            )
            print(100 * "-")

        wm = context.window_manager
        wm.progress_begin(0, 100)
        step = 100 / len(goz_obj_paths)
        for i, ztool_path in enumerate(goz_obj_paths):
            if ztool_path not in gob_import_cache:
                gob_import_cache.append(ztool_path)
                self.GoZit(ztool_path)
            wm.progress_update(step * i)
        wm.progress_end()

        # restore object context
        if context.object and currentContext:
            bpy.ops.object.mode_set(mode=currentContext)

        if utils.prefs().debug_output:
            self.report({"INFO"}, "GoB: Imoprt cycle finished")

        if utils.prefs().performance_profiling:
            start_time = utils.profiler(start_time, "GoB: Total Import Time")
            print(100 * "=")

        return {"FINISHED"}

    def invoke(self, context, event):
        if utils.prefs().debug_output:
            print("ACTION: ", self.action)

        if self.action == "MANUAL":
            run_import_manually()
            return {"FINISHED"}

        if self.action == "AUTO":
            if utils.prefs().import_method == "AUTOMATIC":
                global run_background_update
                if run_background_update:
                    if bpy.app.timers.is_registered(run_import_periodically):
                        bpy.app.timers.unregister(run_import_periodically)
                        if utils.prefs().debug_output:
                            print("Disabling GOZ background listener")
                    run_background_update = False
                else:
                    if not bpy.app.timers.is_registered(run_import_periodically):
                        global cached_last_edition_time
                        GoZ_ObjectList = os.path.join(
                            paths.PATH_GOZ, "GoZBrush", "GoZ_ObjectList.txt"
                        )
                        try:
                            cached_last_edition_time = os.path.getmtime(GoZ_ObjectList)
                        except Exception:
                            f = open(GoZ_ObjectList, "x")
                            f.close()
                        bpy.app.timers.register(
                            run_import_periodically, persistent=True
                        )
                        if utils.prefs().debug_output:
                            print("Enabling GOZ background listener")
                    run_background_update = True
            elif run_background_update:
                if bpy.app.timers.is_registered(run_import_periodically):
                    bpy.app.timers.unregister(run_import_periodically)
                    print("Disabling GOZ background listener")
                run_background_update = False
            return {"FINISHED"}


def run_import_periodically():
    # print("Runing timers update check")
    global cached_last_edition_time, run_background_update

    try:
        file_edition_time = os.path.getmtime(
            os.path.join(paths.PATH_GOZ, "GoZBrush", "GoZ_ObjectList.txt")
        )
        # print("file_edition_time: ", file_edition_time, end='\n\n')
    except Exception as e:
        print(e)
        run_background_update = False
        if bpy.app.timers.is_registered(run_import_periodically):
            bpy.app.timers.unregister(run_import_periodically)
        return utils.prefs().import_timer

    if file_edition_time > cached_last_edition_time:
        cached_last_edition_time = file_edition_time
        bpy.ops.scene.gob_import()  # only call operator update is found (executing operatros is slow)
    else:
        global gob_import_cache
        if gob_import_cache:
            if utils.prefs().debug_output:
                print(
                    "GOZ: clear import cache",
                    file_edition_time - cached_last_edition_time,
                )
            gob_import_cache.clear()  # reset import cache
        elif utils.prefs().debug_output:
            print(
                "GOZ: Nothing to update", file_edition_time - cached_last_edition_time
            )
        return utils.prefs().import_timer

    if not run_background_update and bpy.app.timers.is_registered(
        run_import_periodically
    ):
        bpy.app.timers.unregister(run_import_periodically)

    return utils.prefs().import_timer


def run_import_manually():
    gob_import_cache.clear()
    bpy.ops.scene.gob_import()  # only call operator update is found (executing operatros is slow)
