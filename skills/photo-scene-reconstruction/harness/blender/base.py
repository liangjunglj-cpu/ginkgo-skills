"""Lead's placeholder ground so early renders are not floating in a void. A domain that builds the real ground
sets "<domain>": {"replaces_base": true} in its own layout file, and this module then builds nothing."""
import bpy

import lib


def build(L, ctx):
    if any(isinstance(v, dict) and v.get('replaces_base') for v in L.values()):
        return
    B = L.get('base', {})
    s = B.get('size', 400.0)
    me = bpy.data.meshes.new('BASE_ground')
    me.from_pydata([(-s, -s, -0.02), (s, -s, -0.02), (s, s, -0.02), (-s, s, -0.02)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new('BASE_ground', me)
    me.materials.append(lib.flat_material('BASE_ground', tuple(B.get('color', (0.18, 0.18, 0.18))), rough=B.get('rough', 0.8)))
    lib.link(ob)
