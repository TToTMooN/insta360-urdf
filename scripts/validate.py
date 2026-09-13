"""Validate delivery geometry, portable references, URDF and mass properties."""
from pathlib import Path
import hashlib
import json
import struct
import tempfile
import shutil
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial import ConvexHull
from yourdfpy import URDF

ROOT=Path(__file__).resolve().parents[1]/"models/x5"
path=ROOT/"urdf/insta360_x5.urdf"
tree=ET.parse(path)
for node in tree.findall(".//mesh"):
    assert (path.parent/node.attrib["filename"]).is_file(),node.attrib
robot=URDF.load(str(path),load_collision_meshes=True,build_collision_scene_graph=True)
assert robot.base_link=="x5_link"
assert len(robot.robot.links)==4 and len(robot.robot.joints)==3
scene=trimesh.load_scene(ROOT/"assets/meshes/x5_visual.obj")
visual=scene.to_mesh()
assert np.all(np.isfinite(visual.vertices))
assert np.min(visual.area_faces)>1e-16,"Degenerate OBJ triangles"
expected=np.array([.0382,.046,.1245])
assert np.allclose(visual.extents,expected,atol=1e-7),visual.extents
assert abs(visual.bounds[0,2])<1e-8
assert np.allclose(robot.scene.bounds,visual.bounds,atol=1e-7)
glb=trimesh.load_scene(ROOT/"assets/meshes/x5_visual.glb")
glb.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
assert np.allclose(glb.bounds,visual.bounds,atol=1e-7),glb.bounds
def component(name):
    transform,geometry_name=glb.graph[name]
    result=glb.geometry[geometry_name].copy()
    result.apply_transform(transform)
    return result

# Targets from the official specification and screen-facing product photograph.
display=component("display_active_area")
assert np.allclose(display.extents[1:],[.0339,.0537],atol=1e-7),display.extents
assert component("side_key_panel").bounds[0,1]>.022
assert component("usb_door").bounds[0,1]>0  # Includes the curved lower shoulder.
assert component("battery_cover").bounds[1,1]<-.022
assert component("shutter_outline").bounds[1,1]<0
assert component("menu_front_rectangle").bounds[0,1]>0
assert not any("front_button" in name or "record_symbol" in name for name in glb.geometry)
appearance_checks={"active_display_size_mm":(display.extents[1:]*1000).tolist(),
    "screen_facing_controls":"right (+Y)","screen_facing_battery":"left (-Y)",
    "lower_front_controls":"outlined shutter at -Y; overlapping menu outlines at +Y",
    "basis":"Official X5 specification and product photograph; detail positions remain inferred"}
data=(ROOT/"assets/meshes/x5_visual.glb").read_bytes()
json_length=struct.unpack_from("<I",data,12)[0]
gltf=json.loads(data[20:20+json_length])
assert all("uri" not in b for b in gltf.get("buffers",[])),"External GLB buffer"
assert all("uri" not in i for i in gltf.get("images",[])),"External GLB image"
assert len(gltf["images"])==2
collision=[];halfspaces=[]
for file in sorted((ROOT/"assets/meshes/collision").glob("*.stl")):
    mesh=trimesh.load_mesh(file)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.is_convex
    assert mesh.volume>0 and np.min(mesh.area_faces)>1e-16
    halfspaces.append(ConvexHull(mesh.vertices).equations)
    collision.append({"file":str(file.relative_to(ROOT)),"triangles":len(mesh.faces),"watertight":True,"convex":True})
distance=np.full(len(visual.vertices),np.inf)
for e in halfspaces:
    # Chunk large matrix products to keep checks usable on modest machines.
    for start in range(0,len(visual.vertices),2000):
        end=start+2000
        distance[start:end]=np.minimum(distance[start:end],np.max(visual.vertices[start:end]@e[:,:3].T+e[:,3],axis=1))
assert distance.max()<.0002,f"Collision approximation gap exceeds 0.2 mm: {distance.max()}"
inertia=tree.find(".//inertial/inertia").attrib
diagonal=np.array([float(inertia[k]) for k in ["ixx","iyy","izz"]])
assert np.all(diagonal>0) and 2*diagonal.max()<diagonal.sum()
assert float(tree.find(".//inertial/mass").attrib["value"])==.2
assert np.allclose(robot.get_transform("x5_mount"),np.eye(4))
# Copy to a different location and verify references still resolve.
with tempfile.TemporaryDirectory(prefix="x5-portability-") as tmp:
    target=Path(tmp)
    shutil.copytree(ROOT/"urdf",target/"urdf")
    shutil.copytree(ROOT/"assets/meshes",target/"assets/meshes")
    copied=URDF.load(str(target/"urdf/insta360_x5.urdf"),load_collision_meshes=True)
    assert np.allclose(copied.scene.bounds,visual.bounds,atol=1e-7)
report={
    "status":"PASS", "checks":["URDF graph and local mesh references","URDF load after relocation","meter dimensions and bottom origin","OBJ nondegenerate triangles","GLB embedded textures and matching geometry","positive definite nominal inertia","watertight convex collision meshes","visual vertex coverage within 0.2 mm"],
    "appearance_acceptance":appearance_checks,
    "visual_triangles":len(visual.faces),"visual_bounds_m":visual.bounds.tolist(),
    "dimension_order":"depth X, width Y, height Z", "visual_dimensions_m":visual.extents.tolist(),
    "materials":len(gltf["materials"]),"embedded_texture_images":len(gltf["images"]),
    "collision":collision,"max_visual_vertex_collision_halfspace_gap_mm":float(max(0,distance.max())*1000),
    "mass_kg":.2,"inertia_diagonal_kg_m2":diagonal.tolist(),
    "inertia_basis":"Unmeasured nominal homogeneous-body-box approximation",
    "glb_sha256":hashlib.sha256(data).hexdigest(),
    "not_validated":["dimensional agreement with a measured physical specimen","optical calibration","mass distribution","physics simulator-specific rendering and dynamics"]
}
(ROOT/"docs/validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
