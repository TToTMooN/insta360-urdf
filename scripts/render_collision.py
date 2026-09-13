"""Render the actual URDF collision STL files alongside the visual model.

.venv-blender/bin/python scripts/render_collision.py
.venv/bin/python scripts/make_contact_sheet.py
"""
from pathlib import Path
import math
import struct
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]/'models/x5'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/x5_source.blend'))
visual=list(bpy.context.scene.objects)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1100
scene.render.resolution_y=1400
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=True
scene.view_settings.view_transform='AgX'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.60,.70,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
camera_position=Vector((.23,.15,.137))

def material(name,color,emission=0):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=.65
    shader.inputs['Emission Color'].default_value=(*color,1)
    shader.inputs['Emission Strength'].default_value=emission
    return mat

hulls=[]
wires=[]
for name,color in [('body',(.025,.40,.49)),('front_lens',(.90,.32,.035)),('rear_lens',(.38,.15,.66))]:
    raw=(ROOT/'assets/meshes/collision'/(name+'.stl')).read_bytes()
    count=struct.unpack_from('<I',raw,80)[0]
    dtype=np.dtype([('normal','<f4',3),('points','<f4',(3,3)),('attribute','<u2')])
    triangles=np.frombuffer(raw,dtype=dtype,count=count,offset=84)['points']
    vertices,inverse=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
    faces=inverse.reshape(-1,3)
    mesh=bpy.data.meshes.new('collision_'+name)
    mesh.from_pydata(vertices.tolist(),[],faces.tolist())
    mesh.update()
    obj=bpy.data.objects.new('collision_'+name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material(name+'_solid',color))
    obj.hide_render=True
    hulls.append(obj)
    # Show real hull creases, omitting coplanar triangulation diagonals.
    # No hull inflation or simplification is applied to the STL geometry.
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    normals/=np.linalg.norm(normals,axis=1,keepdims=True)
    facing=np.sum(normals*(np.asarray(camera_position)-triangles.mean(axis=1)),axis=1)>0
    adjacency={}
    for fi,face in enumerate(faces):
        for i in range(3):
            edge=tuple(sorted((int(face[i]),int(face[(i+1)%3]))))
            adjacency.setdefault(edge,[]).append(fi)
    curve=bpy.data.curves.new(name+'_edges','CURVE')
    curve.dimensions='3D'
    curve.bevel_depth=.000065
    curve.bevel_resolution=1
    for (a,b),adj in adjacency.items():
        if not any(facing[i] for i in adj):continue
        if len(adj)==2 and np.dot(normals[adj[0]],normals[adj[1]])>math.cos(math.radians(1.0)):continue
        spline=curve.splines.new('POLY')
        spline.points.add(1)
        spline.points[0].co=(*vertices[a],1)
        spline.points[1].co=(*vertices[b],1)
    wire=bpy.data.objects.new(name+'_edges',curve)
    bpy.context.collection.objects.link(wire)
    wire.data.materials.append(material(name+'_outline',color,.7))
    wires.append(wire)

for name,pos,power,size,color in [('key',(.2,.15,.22),.8,.2,(.91,.95,1)),('rim',(-.12,-.09,.19),1.2,.12,(.65,.78,1)),('fill',(.06,-.2,.04),.5,.15,(1,.92,.83))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((0,0,.063))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('collision_camera');cam=bpy.data.objects.new('collision_camera',data)
bpy.context.collection.objects.link(cam);scene.camera=cam
cam.location=camera_position
cam.rotation_euler=(Vector((0,0,.06))-cam.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=.157;data.clip_start=.001
scene.render.filepath=str(ROOT/'preview/collision_overlay.png')
bpy.ops.render.render(write_still=True)
for obj in visual:obj.hide_render=True
for obj in hulls:obj.hide_render=False
for obj in wires:obj.hide_render=True
scene.render.filepath=str(ROOT/'preview/collision_only.png')
bpy.ops.render.render(write_still=True)
cam.location=(-.23,-.15,.137)
cam.rotation_euler=(Vector((0,0,.06))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/'preview/collision_rear.png')
bpy.ops.render.render(write_still=True)
print('Collision previews rendered from the URDF STL files',flush=True)
