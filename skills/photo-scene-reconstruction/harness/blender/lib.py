"""Shared helpers for a reconstruction run: materials, curves, raycasting."""
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "tex")
GEN = os.path.join(ROOT, "gen")


# ---------------------------------------------------------------- materials
def new_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes['Material Output']
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    return m, nt, bsdf


def _img(nt, path, non_color, vec, box=True):
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(path, check_existing=True)
    if non_color:
        t.image.colorspace_settings.name = 'Non-Color'
    if box:
        t.projection = 'BOX'
        t.projection_blend = 0.3
    nt.links.new(vec, t.inputs['Vector'])
    return t


TEX_DIRS = [TEX]


def ph_paths(tid):
    d = next((os.path.join(t, tid) for t in TEX_DIRS if os.path.isdir(os.path.join(t, tid))), os.path.join(TEX, tid))
    return {k: os.path.join(d, f"{tid}_{k}_2k.jpg") for k in ("diff", "rough", "nor_gl", "disp", "ao")}


def ph_layers(nt, tid, vec, box=True):
    """Return (color, rough, height) sockets for a Poly Haven set."""
    p = ph_paths(tid)
    col = _img(nt, p["diff"], False, vec, box)
    rough = _img(nt, p["rough"], True, vec, box)
    disp = _img(nt, p["disp"], True, vec, box)
    return col.outputs['Color'], rough.outputs['Color'], disp.outputs['Color']


def mapping(nt, coord='Object', scale=1.0, rot=(0, 0, 0), loc=(0, 0, 0)):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    mp.inputs['Scale'].default_value = s
    mp.inputs['Rotation'].default_value = rot
    mp.inputs['Location'].default_value = loc
    nt.links.new(tc.outputs[coord], mp.inputs['Vector'])
    return mp.outputs['Vector'], tc


def math_node(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix_rgb(nt, blend, fac, a, b):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = blend
    sock_f, sock_a, sock_b = n.inputs[0], n.inputs[6], n.inputs[7]
    for s, v in ((sock_f, fac), (sock_a, a), (sock_b, b)):
        if isinstance(v, (int, float)):
            s.default_value = v
        elif isinstance(v, tuple):
            s.default_value = v if len(v) == 4 else (*v, 1.0)
        else:
            nt.links.new(v, s)
    return n.outputs[2]


def bump(nt, height, strength=0.3, distance=0.02, normal=None):
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = distance
    nt.links.new(height, b.inputs['Height'])
    if normal is not None:
        nt.links.new(normal, b.inputs['Normal'])
    return b.outputs['Normal']


def ph_material(name, tid, scale=1.0, tint=None, tint_fac=0.0, bump_str=0.35,
                bump_dist=0.03, rough_mul=1.0, rough_add=0.0, coord='Object', box=True,
                wet_below=None, disp_scale=0.0, rot=(0, 0, 0)):
    """Poly Haven PBR material with box projection and optional waterline wetness."""
    m, nt, bsdf = new_mat(name)
    vec, _ = mapping(nt, coord, scale, rot=rot)
    col, rough, disp = ph_layers(nt, tid, vec, box)
    if tint is not None:
        col = mix_rgb(nt, 'MULTIPLY', tint_fac, col, tint)
    r = math_node(nt, 'MULTIPLY', rough, rough_mul)
    r = math_node(nt, 'ADD', r, rough_add, clamp=True)
    if wet_below is not None:
        col, r = wetness(nt, col, r, wet_below)
    nt.links.new(col, bsdf.inputs['Base Color'])
    nt.links.new(r, bsdf.inputs['Roughness'])
    nt.links.new(bump(nt, disp, bump_str, bump_dist), bsdf.inputs['Normal'])
    if disp_scale:
        dn = nt.nodes.new('ShaderNodeDisplacement')
        dn.inputs['Midlevel'].default_value = 0.5
        dn.inputs['Scale'].default_value = disp_scale
        nt.links.new(disp, dn.inputs['Height'])
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        nt.links.new(dn.outputs[0], out.inputs['Displacement'])
        m.displacement_method = 'BOTH'
    return m


def wetness(nt, col, rough, z_top, band=0.35):
    """Darken + gloss surfaces below world height z_top (splash / tide zone)."""
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs[0])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    nt.links.new(geo.outputs['Position'], noise.inputs['Vector'])
    zz = math_node(nt, 'ADD', sep.outputs['Z'], math_node(nt, 'MULTIPLY', noise.outputs['Fac'], 0.25))
    w = math_node(nt, 'SUBTRACT', z_top, zz)
    w = math_node(nt, 'DIVIDE', w, band)
    w = math_node(nt, 'MINIMUM', math_node(nt, 'MAXIMUM', w, 0.0), 1.0)
    col = mix_rgb(nt, 'MULTIPLY', math_node(nt, 'MULTIPLY', w, 0.55), col, (0.35, 0.36, 0.33, 1))
    rough = math_node(nt, 'SUBTRACT', rough, math_node(nt, 'MULTIPLY', w, 0.45), clamp=True)
    return col, rough


def flat_material(name, color, rough=0.5, metallic=0.0, noise_scale=0.0, noise_amt=0.0,
                  bump_str=0.0, bump_scale=60.0, spec=0.5):
    m, nt, bsdf = new_mat(name)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Specular IOR Level'].default_value = spec
    if noise_amt > 0:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = noise_scale
        nz.inputs['Detail'].default_value = 8
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        f = math_node(nt, 'MULTIPLY', nz.outputs['Fac'], noise_amt)
        c = mix_rgb(nt, 'MULTIPLY', f, (*color, 1), (0.35, 0.33, 0.3, 1))
        nt.links.new(c, bsdf.inputs['Base Color'])
    if bump_str > 0:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = bump_scale
        nz.inputs['Detail'].default_value = 6
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        nt.links.new(bump(nt, nz.outputs['Fac'], bump_str, 0.01), bsdf.inputs['Normal'])
    return m


# ---------------------------------------------------------------- objects
def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def curve_obj(name, pts, radius, mat, coll=None, resolution=6, tilt_twist=False):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    cu.resolution_u = resolution
    sp = cu.splines.new('POLY' if len(pts) < 3 else 'NURBS')
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1.0)
    if sp.type == 'NURBS':
        sp.use_endpoint_u = True
        sp.order_u = 3
    ob = bpy.data.objects.new(name, cu)
    cu.materials.append(mat)
    return link(ob, coll)


def sag_points(a, b, sag, n=24, wobble=0.0, rng=None):
    """Parabolic catenary approximation from a to b with mid-span sag (metres)."""
    a, b = Vector(a), Vector(b)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        p.z -= 4 * sag * t * (1 - t)
        if wobble and rng and 0 < i < n:
            p += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * wobble
        pts.append(tuple(p))
    return pts


def resample(pts, step):
    """Evenly spaced points along a polyline."""
    out = [Vector(pts[0])]
    carry = 0.0
    for i in range(1, len(pts)):
        a, b = Vector(pts[i - 1]), Vector(pts[i])
        seg = (b - a).length
        d = step - carry
        while d <= seg:
            out.append(a.lerp(b, d / seg))
            d += step
        carry = seg - (d - step)
    return out


def mesh_bvh(obj):
    """BVH in object-local space."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(Matrix.Identity(4))
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def bounds_local(obj):
    import numpy as np
    n = len(obj.data.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    return Vector(lo), Vector(hi)
    cs = [Vector(c) for c in obj.bound_box]
    return (Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs))),
            Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs))))
