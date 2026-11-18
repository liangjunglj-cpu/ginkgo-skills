"""Shared mesh helpers (FROZEN: add new functions, never change these).
import_gltf(path, name, coll) -> (root, objs); world_bounds(objs) -> (lo, hi) from vertices;
fit(root, objs, height=None, width=None, at=(x, y), z=0.0, yaw_deg=0) scales uniformly to a measured
height (or width along local X), rotates about Z, and drops the lowest vertex onto z."""
import math

import bpy
from mathutils import Vector


def import_gltf(path, name, coll):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.rotation_mode = 'XYZ'
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    roots = [o for o in new if o.parent is None]
    if len(roots) == 1:
        root = roots[0]
    else:
        root = bpy.data.objects.new(name, None)
        coll.objects.link(root)
        for o in roots:
            o.parent = root
    root.name = name
    root.rotation_mode = 'XYZ'
    return root, new


def world_bounds(objs):
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != 'MESH':
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


def fit(root, objs, height=None, width=None, at=(0.0, 0.0), z=0.0, yaw_deg=0.0):
    root.rotation_euler.z += math.radians(yaw_deg)
    lo, hi = world_bounds(objs)
    s = 1.0
    if height:
        s = height / max(hi.z - lo.z, 1e-6)
    elif width:
        s = width / max(hi.x - lo.x, hi.y - lo.y, 1e-6)
    root.scale = [c * s for c in root.scale]
    lo, hi = world_bounds(objs)
    c = (lo + hi) / 2
    root.location.x += at[0] - c.x
    root.location.y += at[1] - c.y
    root.location.z += z - lo.z
    bpy.context.view_layer.update()
    return world_bounds(objs)
