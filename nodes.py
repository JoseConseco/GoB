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
from . import utils

def create_material_node(mat, diff_texture=None, norm_texture=None, disp_texture=None):
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    output_node = nodes.get('Material Output') 
    shader_node = nodes.get('Principled BSDF')  

    print('Creating material nodes...', shader_node, output_node) 
    

    if utils.prefs().import_material is not None: 
        #create main shader node if it does not exist to attach the texture nodes to
        if not output_node:      
            output_node = nodes.new('ShaderNodeOutputMaterial')
            output_node.location = 400, 400 

        if not shader_node:
            print('Creating Principled BSDF shader node...')
            shader_node = nodes.new('ShaderNodeBsdfPrincipled')
            shader_node.location = 0, 400 
        mat.node_tree.links.new(output_node.inputs[0], shader_node.outputs[0])
 


    if utils.prefs().import_material == 'TEXTURES': 
        node_cache = [node.label for node in nodes]
        # create the Diffiuse Color nodes
        #image_node = nodes.get('Image Texture') # ShaderNodeTexImage Image Texture
        diff_texture_node = None 
        if 'Diffuse Color Map' not in node_cache: 
            diff_texture_node = nodes.new('ShaderNodeTexImage')
            diff_texture_node.location = -700, 500  
            diff_texture_node.image = diff_texture
            diff_texture_node.label = 'Diffuse Color Map'            
            if diff_texture:
                diff_texture_node.image.colorspace_settings.name = utils.prefs().import_diffuse_colorspace
            mat.node_tree.links.new(shader_node.inputs[0], diff_texture_node.outputs[0])

        # create the Normal Map nodes   
        norm_node = nodes.get('Normal Map')     # ShaderNodeNormalMap Normal Map     
        if not norm_node:
            norm_node = nodes.new('ShaderNodeNormalMap')
            norm_node.location = -300, -100  
        if bpy.app.version < (3,1,0):
            mat.node_tree.links.new(shader_node.inputs[20], norm_node.outputs[0])
        else:
            mat.node_tree.links.new(shader_node.inputs[22], norm_node.outputs[0])

        norm_texture_node = None 
        if 'Normal Map' not in node_cache:   
            norm_texture_node = nodes.new('ShaderNodeTexImage')
            norm_texture_node.location = -700, -100  
            norm_texture_node.image = norm_texture
            norm_texture_node.label = 'Normal Map'          
            if norm_texture:
                norm_texture_node.image.colorspace_settings.name = utils.prefs().import_normal_colorspace
            mat.node_tree.links.new(norm_node.inputs[1], norm_texture_node.outputs[0])

        # create the Displacement nodes   
        disp_node = nodes.get('Displacement')   # ShaderNodeDisplacement Displacement       
        if not disp_node:
            disp_node = nodes.new('ShaderNodeDisplacement')
            disp_node.location = -300, 200  
        mat.node_tree.links.new(output_node.inputs[2], disp_node.outputs[0])

        disp_texture_node = None                
        if 'Displacement Map' not in node_cache:     
            disp_texture_node = nodes.new('ShaderNodeTexImage')
            disp_texture_node.location = -700, 200  
            disp_texture_node.image = disp_texture
            disp_texture_node.label = 'Displacement Map'
            if disp_texture:
                disp_texture_node.image.colorspace_settings.name = utils.prefs().import_displace_colorspace
            mat.node_tree.links.new(disp_node.inputs[0], disp_texture_node.outputs[0])
    

    if utils.prefs().import_material == 'POLYPAINT':
        vcol_node = None 
        
        vcol_node = [nodes.get(node.name) for node in nodes if node.bl_idname == 'ShaderNodeVertexColor' and utils.prefs().import_polypaint_name in node.layer_name]

        if not vcol_node:
            vcol_node = nodes.new('ShaderNodeVertexColor')
            vcol_node.location = -300, 200
            vcol_node.layer_name = utils.prefs().import_polypaint_name    
            mat.node_tree.links.new(shader_node.inputs[0], vcol_node.outputs[0])


    if utils.prefs().import_material == 'POLYGROUPS':
        pass
