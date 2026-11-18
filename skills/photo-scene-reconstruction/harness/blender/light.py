"""Light domain: physical sky, sun, exposure and colour management from layout/light.json.
Sun azimuth is measured from world +Y toward +X (degrees); elevation above the horizon.
Only the light domain (or the lead) edits this module and light.json; other domains never touch exposure."""
import math

import bpy
from mathutils import Vector


def _sky_enum():
    ids = [i.identifier for i in bpy.types.ShaderNodeTexSky.bl_rna.properties['sky_type'].enum_items]
    for k in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE', 'PREETHAM'):
        if k in ids:
            return k
    return ids[0]


def sun_dir(elev, azim):
    e, a = math.radians(elev), math.radians(azim)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


def build(L, ctx):
    P = L['light']
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    w = bpy.data.worlds.new('LAB_world'); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = _sky_enum()
    for attr, val in (('sun_elevation', math.radians(P['sun_elev'])), ('sun_rotation', math.radians(-P['sun_azim'])),
                      ('altitude', P.get('altitude', 0.0)), ('air_density', P.get('air', 1.0)),
                      ('dust_density', P.get('dust', 1.0)), ('ozone_density', 1.0), ('sun_disc', False)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
    try:  # sky rotation convention differs between sky models; keep the sky's sun glow on our sun
        sky.sun_rotation = math.radians(90 - P['sun_azim'])
    except Exception:
        pass
    # the physical sky is far bluer than a photographer's white-balanced daylight: desaturate it for lighting
    # (sky_sat, 1 = physical) and optionally tint it; the sun keeps its own colour
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = P.get('sky_sat', 0.5)
    nt.links.new(sky.outputs['Color'], hs.inputs['Color'])
    tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1.0
    nt.links.new(hs.outputs['Color'], tint.inputs['A'])
    tint.inputs['B'].default_value = (*P.get('sky_tint', (1.0, 1.0, 1.0)), 1)
    nt.links.new(tint.outputs['Result'], bg.inputs['Color'])
    if P.get('overcast'):   # measured overcast: near-uniform neutral dome, brighter at the zenith, weak sun
        o = P['overcast']
        grad = nt.nodes.new('ShaderNodeTexGradient'); grad.gradient_type = 'LINEAR'
        tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])   # world Generated = view direction
        mr = nt.nodes.new('ShaderNodeMapRange')
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        mr.inputs['From Min'].default_value = -0.2; mr.inputs['From Max'].default_value = 1.0
        mr.inputs['To Min'].default_value = o.get('horizon', 0.75); mr.inputs['To Max'].default_value = o.get('zenith', 1.15)
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        mix.inputs['A'].default_value = (*o.get('color', (0.97, 0.99, 1.0)), 1)
        nt.links.new(mr.outputs['Result'], mix.inputs['B'])
        nt.links.new(mix.outputs['Result'], bg.inputs['Color'])
        nt.nodes.remove(grad)
    bg.inputs['Strength'].default_value = P.get('sky_strength', 0.35)
    sd = bpy.data.lights.new('LGT_sun', 'SUN')
    sd.energy = P.get('sun_strength', 4.0)
    sd.angle = math.radians(P.get('sun_angle', 0.8))
    sd.color = P.get('sun_color', (1.0, 0.96, 0.9))
    so = bpy.data.objects.new('LGT_sun', sd)
    d = sun_dir(P['sun_elev'], P['sun_azim'])
    so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(so)
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = P.get('look', 'AgX - Medium High Contrast')
    except Exception:
        pass
    sc.view_settings.exposure = P.get('exposure', 0.0)
    sc.cycles.max_bounces = 8
    if P.get('mist'):   # aerial perspective: volume-free haze as a world-colour blend handled by the render later
        sc['lab_mist'] = P['mist']
    ctx['sun_dir'] = d
