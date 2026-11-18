"""Build this lab's scene. FROZEN (lead only).
blender -b --factory-startup -P blender/build_scene.py -- out.blend [only=a,b]

Orchestration only: merge layout/*.json into L, create the camera from layout/camera.json, call each domain's
build(L, ctx) in the order of layout/order.json, save. No geometry lives here. Domains listed in
order.json "always" are built even with only=."""
import glob
import json
import math
import os
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, 'tools')]
import lib  # noqa: E402

L = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'layout', '*.json'))):
    L.update(json.load(open(f, encoding='utf8')))


def _merge(a, b):
    for k, v in b.items():
        if k.startswith('_'):
            continue
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _merge(a[k], v)
        else:
            a[k] = v


for _mf in filter(None, os.environ.get('LAB_MOOD', '').split(',')):   # mood overlays, layout untouched
    _merge(L, json.load(open(_mf, encoding='utf8')))
    print('[mood]', _mf)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = next((a for a in argv if a.endswith('.blend')), os.path.join(ROOT, 'work', 'main.blend'))
only = next((a.split('=', 1)[1].split(',') for a in argv if a.startswith('only=')), None)

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'

C = L['camera']
cd = bpy.data.cameras.new('CAM_hero')
cd.lens = C['focal_mm']
cd.sensor_fit = 'VERTICAL'
cd.sensor_height = C['sensor_h']
cd.clip_start = 0.1
cd.clip_end = 5000
co = bpy.data.objects.new('CAM_hero', cd)
co.location = C['pos']
co.rotation_euler = (math.radians(90 + C['pitch']), math.radians(C.get('roll', 0.0)), math.radians(C['yaw']))
lib.link(co)
sc.camera = co
sc.render.resolution_x, sc.render.resolution_y = C['res']
# extra cameras (hero close-up etc.) for proof renders: L['cameras'] = {name: same keys}
for name, cc in L.get('cameras', {}).items():
    d = bpy.data.cameras.new('CAM_' + name); d.lens = cc['focal_mm']; d.sensor_fit = 'VERTICAL'
    d.sensor_height = cc['sensor_h']; d.clip_start = 0.05; d.clip_end = 5000
    o = bpy.data.objects.new('CAM_' + name, d); o.location = cc['pos']
    o.rotation_euler = (math.radians(90 + cc['pitch']), math.radians(cc.get('roll', 0.0)), math.radians(cc['yaw']))
    lib.link(o)

ctx = {'camera': co, 'root': ROOT}
ORD = L['order']
failed = []
for key, modname in ORD['modules']:
    if only and key not in only and key not in ORD.get('always', []):
        continue
    try:
        mod = __import__(modname)
        mod.build(L, ctx)
    except Exception:                       # one broken domain must not block everyone else's loop
        traceback.print_exc()
        failed.append(key)
        print('[FAILED]', key)
        continue
    bpy.context.view_layer.update()
    print('[built]', key)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('[saved]', OUT, 'failed=' + ','.join(failed))
