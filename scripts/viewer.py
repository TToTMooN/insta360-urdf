"""Local viser viewer: .venv/bin/python scripts/viewer.py --port 8080"""
from pathlib import Path
import argparse
import json
import time
import numpy as np
import trimesh
import viser

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--port",type=int,default=8080);ap.add_argument("--host",default="127.0.0.1")
    available=sorted(p.name for p in (ROOT/"models").iterdir() if (p/"model.json").is_file())
    ap.add_argument("--model",choices=available,default="x5")
    args=ap.parse_args()
    model_dir=ROOT/"models"/args.model
    meta=json.loads((model_dir/"model.json").read_text())
    params=json.loads((model_dir/meta["config"]).read_text())
    server=viser.ViserServer(host=args.host,port=args.port,label=meta["name"]+" · Visual asset")
    server.gui.configure_theme(dark_mode=True,control_layout="collapsible",show_logo=False,show_share_button=False,brand_color=(58,185,206))
    server.scene.set_up_direction("+z")
    server.scene.configure_default_lights(False)
    server.scene.configure_environment_map("studio",environment_intensity=1.2)
    # Standard glTF is Y-up. Rotate its root +90 deg about X into robotics Z-up.
    visual=server.scene.add_glb("/camera_visual",(model_dir/meta["visual"]).read_bytes(),wxyz=(2**-.5,2**-.5,0,0))
    wire=[]
    for path in sorted((model_dir/"assets/meshes/collision").glob("*.stl")):
        mesh=trimesh.load_mesh(path)
        wire.append(server.scene.add_mesh_simple("/collision/"+path.stem,mesh.vertices,mesh.faces,color=(53,215,229),wireframe=True,visible=False,opacity=.55))
    axes=server.scene.add_frame("/mount",axes_length=.03,axes_radius=.00035,visible=False)
    grid=server.scene.add_grid("/ground",width=.35,height=.35,cell_size=.01,section_size=.05,plane="xy",position=(0,0,-.0005),cell_color=(60,64,74),section_color=(89,98,113),plane_color=(32,35,43),plane_opacity=.9,shadow_opacity=.2)
    stats=json.loads((model_dir/"assets/visual_manifest.json").read_text())
    server.gui.add_markdown(f"## {meta['name']}\nIndependent procedural reconstruction.\n\n**{params['width_mm']:g} × {params['height_mm']:g} × {params['overall_depth_mm']:g} mm · {params['mass_kg']*1000:g} g**\n\nPBR visual mesh · meter units · bottom mount origin")
    mode=server.gui.add_dropdown("Display",["PBR visual","Visual + collision","Collision only"])
    @mode.on_update
    def _(_event):
        visual.visible=mode.value!="Collision only"
        for item in wire:item.visible=mode.value!="PBR visual"
    show_axes=server.gui.add_checkbox("Mount axes",False)
    @show_axes.on_update
    def _(_event):axes.visible=show_axes.value
    show_grid=server.gui.add_checkbox("Ground / 10 mm grid",True)
    @show_grid.on_update
    def _(_event):grid.visible=show_grid.value
    light=server.gui.add_slider("Studio light",min=.15,max=2.0,step=.05,initial_value=1.2)
    @light.on_update
    def _(_event):server.scene.configure_environment_map("studio",environment_intensity=light.value)
    views={"Front ¾":(.22,.145,.135),"Back ¾":(-.22,-.145,.135),"Front":(.28,0,.06225),"Back":(-.28,0,.06225),"Controls (+Y)":(0,.28,.06225),"Battery (−Y)":(0,-.28,.06225),"Bottom":(.10,.10,-.20)}
    scale=params["height_mm"]/124.5
    views={name:tuple(v*scale for v in pos) for name,pos in views.items()}
    def set_view(client,name):
        client.camera.up_direction=(0,0,1)
        client.camera.position=views[name]
        client.camera.look_at=(0,0,.060*scale)
        client.camera.fov=.58
        client.camera.near=.001
        client.camera.far=10
    with server.gui.add_folder("Viewpoints"):
        for name in views:
            button=server.gui.add_button(name)
            @button.on_click
            def _(event,name=name):
                if event.client is not None:set_view(event.client,name)
    server.gui.add_markdown(f"**{sum(x['triangles'] for x in stats):,} triangles** · {len(stats)} materials\n\nDrag to orbit · scroll to zoom\n\n**Accuracy:** published envelope, active screen size and mass; inferred detail geometry. COM/inertia estimated. No optical calibration.\n\nOrigin: bottom mount. +X screen, +Y screen-facing right, +Z up.")
    @server.on_client_connect
    def _(client):set_view(client,"Front ¾")
    print(f"{meta['name']} viewer ready: http://{args.host}:{args.port}",flush=True)
    while True:time.sleep(.25)

if __name__=="__main__":main()
