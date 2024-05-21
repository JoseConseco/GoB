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
import mathutils

from bpy.types import Object
from . import utils


def prefs():
    user_preferences = bpy.context.preferences
    return user_preferences.addons[__package__].preferences 


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
    
    if prefs().use_scale == 'BUNITS':
        scale = 1 / bpy.context.scene.unit_settings.scale_length

    if prefs().use_scale == 'MANUAL':        
        scale =  1 / prefs().manual_scale

    if prefs().use_scale == 'ZUNITS':
        if bpy.context.active_object:
            obj = bpy.context.active_object
            i, max = utils.max_list_value(obj.dimensions)
            scale =  1 / prefs().zbrush_scale * max
            if prefs().debug_output:
                print("unit scale 2: ", obj.dimensions, i, max, scale, obj.dimensions * scale)
            
    #import
    if prefs().flip_up_axis:  # fixes bad mesh orientation for some people
        if prefs().flip_forward_axis:
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
        if prefs().flip_forward_axis:            
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