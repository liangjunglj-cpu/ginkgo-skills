"""Render a built lab blend. FROZEN (light domain may extend via scene['lab_post'] later).
blender -b work/x.blend -P blender/render.py -- out.png [width] [spp] [x0 y0 x1 y1] [cam=name] [clay]
Box is in target-image pixels (layout/camera.json res). cam=hero renders CAM_hero (default) or CAM_<name>
at that camera's own res aspect. 'clay' overrides every material with grey clay (form check)."""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
nums = [a for a in argv[1:] if not ("=" in a or a == "clay")]
w = int(nums[0]) if len(nums) > 0 else 960
spp = int(nums[1]) if len(nums) > 1 else 32
box = [float(v) for v in nums[2:6]] if len(nums) >= 6 else None
camname = next((a.split("=", 1)[1] for a in argv if a.startswith("cam=")), "hero")
sc = bpy.context.scene
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJ = json.load(open(os.path.join(ROOT, "layout", "camera.json")))
res = CJ["camera"]["res"] if camname == "hero" else CJ.get("cameras", {}).get(camname, CJ["camera"]).get("res", CJ["camera"]["res"])
cam = bpy.data.objects.get("CAM_" + camname)
if cam:
    sc.camera = cam
prefs = bpy.context.preferences.addons['cycles'].preferences
for dev in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = dev
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == dev
        break
    except Exception:
        continue
sc.render.engine = "CYCLES"
sc.cycles.device = 'GPU'
sc.render.resolution_x = w
sc.render.resolution_y = int(round(w * res[1] / res[0]))
sc.render.resolution_percentage = 100
if box:
    bx0, by0, bx1, by1 = box
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x = bx0 / res[0], bx1 / res[0]
    sc.render.border_min_y, sc.render.border_max_y = 1 - by1 / res[1], 1 - by0 / res[1]
if "clay" in argv:
    clay = bpy.data.materials.new("CLAY"); clay.use_nodes = True
    b = next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1); b.inputs["Roughness"].default_value = 0.8
    vl = sc.view_layers[0]
    vl.material_override = clay
sc.cycles.samples = spp
try:
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
except Exception as e:
    print('[render] denoiser settings skipped:', e)
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.02 if spp < 200 else 0.008
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '8'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('[render] wrote', out)
