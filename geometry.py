from bpy.types import Object


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