---
name: photo-scene-reconstruction
description: Rebuild a reference photo as a Blender scene that reads as a photograph from the same camera, using a multi-agent harness with owned domains, a render-and-compare loop, a fixed fidelity order, light and materials measured from the photo (sun from shadows, off-camera shade, sensor finish, albedo checks), a real-mesh sourcing rule (no primitive stand-ins for complex objects) and a ranked list of code-generation techniques for detailed, organic buildings (section 7). Use when the user asks for buildings generated in code, or when the user asks to recreate, reconstruct or match a photo or reference image in 3D, to raise the fidelity or realism of a generated scene, or to set up agents to build a scene in parallel.
---

# Photo scene reconstruction

This method was developed on three projects in November 2026: a street photo with a tram (Freiburg), a
square with a Gothic fountain (the Fischbrunnen, Freiburg) and three code-generated city, shop and harbour
dioramas. The examples below come from them. The generic harness (camera, orchestrator, render and compare
tools) is in `harness/` next to this file: copy `harness/blender` and `harness/tools` into a new run folder.
Tool names written below that are not in `harness/` (for example `facade_solve.py`) are per-domain probes
that each run writes for itself; their purpose is described where they are named.

Requirements: Blender (written against 5.1, Cycles), Python with numpy, opencv and pillow for the 2D tools
(`tools/py.sh` runs them with `uv`), and an agent runtime that can start sub-agents.

The user judges fidelity by eye, side by side with the photo. Everything below exists to make that
comparison cheap, frequent and honest.

## 0. Lead sets up before any agent starts

The lead (the main session) does these alone. Agents start only when all are done.

1. **Run folder.** `<runs>/<scene>/` with `ref/photo.jpg`, `blender/`, `tools/`, `layout/`, `gen/`, `renders/`,
   `work/`, `final/`. Copy `lib.py`, `arch.py`, `assets.py`, `render.py`, `build_scene.py` and the generic
   tools (`cam.py`, `vp.py`, `solve_cam.py`, `iterate.sh`, `overlay.py`, `edges.py`, `pair.py`, `crop.py`,
   `stats.py`, `py.sh`, `fetch_polyhaven.py`, `fetch_ph_model.py`) from `harness/`.
2. **Solve the camera** with `tools/vp.py`. Find the vertical vanishing point and one horizontal vanishing
   point along the main facade. `tools/solve_cam.py` then gets:
   - the focal length, from the two directions being at right angles (do not assume a lens);
   - the pitch, from the vertical vanishing point;
   - the yaw, chosen so the facade runs along world +X.

   Write the result to `layout/camera.json`. The camera is then frozen for the whole run.
3. **Measure anchors** with `tools/cam.py`:
   - `on_z` hits a horizontal plane, `on_y` a vertical plane, `project` gives a pixel, and `ray` gives
     a view ray.
   - Measure the ground lines, facade planes and the distance of each landmark.
   - Write the lead's first estimates into the rulebook as starting values.
   - At grazing angles one pixel of a ground line can be half a metre of depth. Prefer the heights and
     widths of known things (door 2.1 m, eye 1.6 m, kerb 0.12 m) over single ground points.
4. **Object inventory.** List every object visible in the photo and mark each as *scripted* or *mesh*
   (section 3). This list decides the domain split and the asset fetches.
5. **Write `AGENTS.md`** for the run: goal, world frame, anchors, domain table, hard rules, the loop,
   the working order, the finish rule.

## 1. Domain usership (how agents share one scene)

### Splitting the scene
- One domain = one module with `build(L, ctx)` + one `layout/<domain>.json` + one file prefix for anything
  new (`tools/<domain>_*.py`, `tex/<domain>_*`, `gen/<domain>_*`).
- Split by **screen area and kind of work**, not by object count. A good split gives each agent a region it
  can crop and judge alone. Freiburg used five: light, street, left buildings, hero facade, props.
- **Light is always its own domain** and owns sky, exposure, colour management and the grade. No other
  agent touches exposure to make its own material look right.
- The hero element (the thing the eye lands on) gets a domain to itself.
- Four to six domains. Fewer and agents collide inside a file; more and the lead cannot review them.

### Contracts
- `build_scene.py` only orchestrates: merge `layout/*.json` into `L`, create the camera, call each
  module in a fixed order, save. No geometry lives there.
- Every agent may READ any layout key and may WRITE only its own layout file and module.
- Shared helpers (`lib.py`, `arch.py`, `assets.py`, `cam.py`, `iterate.sh`) are frozen. An agent that
  needs a changed helper copies it into its own module under a new name. `assets.py` holds the mesh-fitting
  steps so every domain fits meshes the same way:
  - `import_gltf` imports and sets XYZ rotation;
  - `world_bounds` computes bounds from vertices;
  - `fit` scales to a measured height or width, yaws, and drops the lowest vertex onto its support.
- **The domain that measures an anchor owns it.** The lead's anchors are starting values. The owning domain
  refines them and publishes the result in its layout file, for example `L['facade']['plane_y']` or
  `L['fountain']['centre']`. Every other domain reads the value from `L` and never copies the number into
  its own code, so a refinement reaches everyone on the next build.
- Store measurements in photo pixels next to the derived world values (for example `facade.px` beside
  `facade.sec`). A solver script (`tools/facade_solve.py`) turns pixels into world numbers and writes them
  into the layout. Re-measuring then means editing a pixel and re-running the solver, not hand-editing
  coordinates.
- Names that other modules import are listed in the rulebook with the rule "add new functions, never change
  these". Cross-domain values travel through `ctx` (for example `ctx['track_x']`), not through edits.
- `build(L, ctx)` must work at all times. Every agent rebuilds the whole scene, so one broken module blocks
  everyone. Check syntax before saving a risky edit.

### Running the agents
- Each agent builds into its own `work/<domain>.blend`; renders are serialised by `work/.gpu_lock`
  (a lock older than 6 minutes is stale). `only=` skips other domains for speed; use the full scene when
  judging colour, because neighbours bounce light.
- **At most two or three agents that render at once.** Several Blender processes grew the Windows pagefile
  past 50 GB and filled C:. Delete an agent's `work/<domain>.blend` as soon as it finishes. Wait on a
  specific process ID, never on "no Blender running".
- **Run in waves.** Wave 1 is the domains that make geometry (for example ground, facade and the hero),
  at most three at once. Wave 2 is light and the organic or furniture domain, which need the geometry to
  light, shade and grow onto. Light judged on unfinished geometry is wasted work.
- **Keep the machine awake** (`request_keep_awake`) before any wave. When the PC idle-slept, renders froze
  for nine hours.
- **Rounds.** After each wave or round, the lead builds `main`, reviews the render against the photo by eye,
  and writes the worst differences as the next round's briefs. The user's notes on a sent comparison sheet,
  for example "rougher texture" or "lighting looks artificial", become a round of their own.
- Each agent keeps its last three preview sets in `renders/` and deletes older ones of its own prefix.
- Agents never spend paid credits. They report what a generated asset would fix, with the photo crop to use;
  the lead takes that to the user with the cost.
- Agents do not commit, do not touch git and do not write outside the run folder.

### Agent brief (what the lead sends)
Keep it short; the rulebook carries the rest.
- "Read `AGENTS.md` first." Then: your domain, your module and layout file, your photo region in pixels.
- What is already there and what is wrong with it (name the worst three differences from the photo).
- The mesh list for that domain from the inventory, already fetched into `gen/`.
- The finish rule and report format (below).

### Finish and integration
- An agent stops when its area holds up in a 960 px crop next to the photo, or after about 12 iterations.
- Final report, under 250 words: what changed, what still differs from the photo, where a generated asset
  would help, the tag of the last render.
- The lead then builds `work/main.blend` from all modules, renders the full frame, and reviews it against
  the photo **without reading the agents' reports first**. Reports describe intentions; the image is the
  evidence. Differences become the next round's briefs.
- Lighting moods and effects are applied afterwards as a non-destructive overlay on `main.blend`
  so a look change never disturbs approved fidelity. The tram run used `blender/mood.py` on top of
  `main.blend`. Fischbrunnen deep-merges `mood/<variant>.json` (written by `tools/mood_make.py`) over the
  layouts when `FB_MOOD` is set; it takes a comma list, for example `warm_a,film`. Use the Fischbrunnen
  form: the mood rebuilds through the same modules and needs no second scene file.

## 2. Fidelity order and the loop

### The loop, on every change
```
tools/iterate.sh <domain> <n> [width=480] [spp=24] [only=a,b] [x0 y0 x1 y1]
```
It builds, renders, and writes `ovl_*` (photo | render | 50% blend) and `edg_*` (photo edges in red over the
render with a pixel grid). With a box in photo pixels it renders only that region and writes `crop_*`
(photo crop | render crop, enlarged); at width 960 that takes about 25 s. Open the images and look at them.
Never report a change as an improvement without having viewed the comparison.

### Work in this order; do not skip ahead
Each stage has a gate. Detail added before an earlier gate passes is wasted, because it moves when the
earlier error is fixed.

| stage | what to do | gate before moving on |
|---|---|---|
| 1. Read | Enlarge the photo crop of your area. Write down what is actually there: counts, materials, what touches what. | A written list exists; every item is in the inventory. |
| 2. Silhouette | Place masses from `cam.py` measurements. | Outlines sit on the red edges in `edg_*` within a few pixels at 960 wide. |
| 3. Proportion | Openings, floor lines, bays, repeat counts. | Window and door edges line up with the photo edges; counts match. |
| 4. Colour | Material base colours measured against the photo, full scene built, light domain's exposure untouched. Compare material versions as albedo (section 4.2). | `tools/stats.py` and the domain's region checks are close to the photo, and the 50% blend shows no tinted patches. |
| 5. Small parts | Trims, fixings, cables, signs, gutters, lamps, street clutter. Meshes per section 3. | Every inventory item for the area exists in the crop. |
| 6. Variation and wear | Bevels, colour variation, stains under sills, streaks, ground wear, glass ripple and reflections. | The crop passes the CG-tell check below, and the texture-energy check (section 4.3) is close to the photo. |

Rules that hold at every stage:
- Real-world dimensions, in millimetres for patterns. Measure with `cam.py`; do not guess.
- Nothing floats or interpenetrates. Things stand on the ground or are fixed to a wall.
- One change per iteration when chasing a difference, so the comparison shows what the change did.

### CG-tell check (after every render: "what still tells me this is CG?")
| tell | usual fix |
|---|---|
| Perfectly sharp edges | Bevel or chamfer, 2 to 10 mm on built parts |
| Flat single-colour surface | Measured colour variation, stains, streaks, texture at true scale |
| Visible repetition | Per-instance variation in tone, rotation, wear |
| Missing contact shadow | Check the object touches the ground; check light and denoise |
| Glass with nothing behind or reflected | Interior plane or tint, real reflection, slight ripple |
| Wrong texture scale | Re-measure the pattern in millimetres from the photo |
| Primitive-shaped object | Replace with a real mesh (section 3) |
| Too clean ground | Wear, damp patches, leaves, joints |

### After the user approves fidelity
Only then do these, in order:
1. **Realism pass:** bevels, glass and ground wear. The tram run did this as one module
   (a `weather` module); Fischbrunnen did it inside each domain. Either works, but one domain must own
   each surface.
2. **Render quality:** 2160 px supersample and accurate denoise.
3. **Sensor finish** (section 4.1).
4. **Proof views** from other angles (a `proof.py` that renders extra cameras).
5. **Lighting moods.**
6. **Film** (section 5).

Send a photo-versus-render sheet at each of these checkpoints and wait for the user.

## 3. Meshes: no primitives for complex objects

Rule: complex objects are never built from simple primitive geometry. Use an existing
real mesh instead.

### What counts
- **Scripted geometry is allowed** for architecture and infrastructure: walls, slabs, roofs, window and door
  frames, cornices and profiled trims, kerbs, paving, rails, poles, wires, flat signs.
- **A real mesh is required** for everything organic or object-like: trees, shrubs, potted plants, people,
  vehicles, bicycles, chairs, tables, benches, planters, parasols, lamps with shaped bodies, sculpted
  ornaments, statues, fabric with folds.
- Test: if a person would describe your build as "a sphere on a stick", "a box with four legs" or "a
  cylinder", it is a primitive stand-in and is not allowed, even as a placeholder in a render sent to the
  user.

### Sourcing ladder (stop at the first that fits)
1. **Your own mesh library.** Keep an index (category, size, triangle count, path, licence) of every prop
   mesh earlier projects produced or downloaded, and search it first. Reuse beats buying.
2. **Poly Haven CC0**, free: `tools/fetch_ph_model.py <id>` (glTF 2k into `gen/ph/<id>/`), textures and
   skies with `tools/fetch_polyhaven.py <id>`. Keep downloads under about 150 MB per agent.
3. **Generated mesh**, paid, only through the lead and only after the user has seen the cost: Meshy for
   soft or organic props and ornaments, Tripo H3.1 detailed for hard-surface heroes. Prepare and fit the
   mesh in three steps:
   - **Clean the crop.** Crop the object from the photo (`gen/meshy_refs/<name>_crop.jpg`). Run one cheap
     image-edit pass on it to remove occluders, finish cut-off parts and give
     a plain background, saving `<name>_clean.png`. Only then call image-to-3D. On the fountain run this made
     all four statues and the canopy usable on the first try.
   - **Decimate once,** offline, into `gen/<domain>_meshes.blend` with a face budget per object (for
     example `tools/fountain_prep.py`). Every rebuild then loads the light copy, not the raw GLB.
   - **Fit with `assets.fit`** to the size measured from the photo.
4. **Nothing fits and no approval yet:** leave the object out and name it in the report. A gap is honest;
   a primitive stand-in is not.

**Procedural plants grown from the photo count as real plants.** On Fischbrunnen, `tools/life_vines.py`
grew climbing vines in three steps:
1. It segmented the vine masses in the photo.
2. It grew a branching stem tree through them and stored leaf samples with foliage depth, all in photo
   pixels, in `gen/life_vines.npz`.
3. `fb_life.py` raycast those samples from the solved camera onto the facade walls (`ctx['facade_walls']`)
   and instanced real leaf images with alpha on them.

The plant then has the photo's shape and real foliage. Blob spheres or a noise-displaced shell are still
primitives.

### Fitting a mesh into the scene
- Scale to the dimension measured from the photo, not to the asset's own size.
- glTF imports arrive in quaternion mode: set `rotation_mode='XYZ'` before using euler angles. `bound_box`
  is stale after transforms; compute bounds from vertices and drop the lowest vertex onto the ground.
- Adjust base colour toward the photo measurement; keep the asset's roughness and normal detail.
- Record each placed mesh in the domain's layout file: asset id, source, position, scale, rotation.
- A close match that is a real mesh beats an exact match built from boxes. Say in the report where the
  mesh differs from the photo.

## 4. Measure, do not tune

The second run's main lesson: anything that can be measured from the photo should be, and turned into a
script that prints numbers. Agents tuning by eye drift, and two agents tuning against each other
oscillate. Each domain writes its probes as `tools/<domain>_*.py`; the ones below are worth copying.

### 4.1 Light (the light domain)
- **Sun direction from shadows in the photo.** Pick two or three crisp shadow edges, such as a bay's
  shadow on a roof skirt, a fin's shadow on a recessed shopfront, or an eave's shadow on a wall. Trace them
  against the scene geometry analytically, without Blender, and solve the sun's azimuth and elevation
  (`tools/light_sunfit.py`, `light_roofshadow.py`). Do this before any render, because every material
  judgement depends on it.
- **Shade from off-camera casters.** Trees and buildings behind the camera still print shadows on the
  scene:
  1. Measure the sun fraction of every pixel on sunlit materials (`tools/light_fmap.py` → `gen/light_fmap.npy`).
  2. Trace each texel of a vertical screen between camera and scene along the sun onto the model.
  3. Give each texel the measured sun fraction (`tools/light_gobo.py` → `tex/light_gobo.png`).
  4. Place it as a shadow-only screen, invisible to camera, diffuse and glossy rays.

  This prints the shadow that is actually in the photo; invented tree crowns did not. A gobo baked for one
  sun elevation slides at another, so rebake it for a mood with a different sun.
- **Fit the sky as a dome.** `tools/light_skyfit.py` fits the clear-sky colour as a smooth function of
  elevation and of the angle to the sun (a node grid in `light.json` `cam_sky`). It also maps cloud
  density in world azimuth and elevation (`tex/light_clouds.png`). The sky then stays right when the
  camera moves, which a screen overlay cannot do.
- **Match the sensor, not only the light.** A phone photo has a signature: noise that depends on
  brightness, luma sharpening, a vignette, highlight bloom and veil.
  - `tools/light_sensor.py` and `light_noisefloor.py` measure each of these in flat patches and per
    brightness band, for the photo and for a render.
  - `render.py` applies the same finish from a `sensor` block in `light.json`.
  - Clean, noiseless CG reads as "artificial lighting" even when the light itself is right. This round
    answered the user's note.
- **Judge sun and shade separately.** `tools/light_fclass.py` splits each area into shade (sun fraction
  below 0.25) and sun (above 0.75) and compares the luminance of each with the photo. An averaged region
  hides a sun that is too strong under a shade that is too dark.
- Haze: visibility under about 4000 m turns a clear sky milky.

### 4.2 Material colour as albedo (every material domain)
Lit comparisons mix material and light errors, and agents then fix their materials to make up for the
light domain's exposure. Compare base colours with the light removed:
- `tools/facade_albedo.py` renders every `<domain>_*` material's base colour as emission, with lights and
  world off and the Standard view transform.
- `tools/facade_albcmp.py` compares two such renders per region, as sRGB means and a linear ratio, masking
  occluders.

Use it to A/B two versions of a material under any light. Keep the old version reachable behind a switch
in the layout (for example `fountain.stone.legacy`) so the comparison can be repeated.

### 4.3 Texture energy (realism)
`tools/facade_hf.py` compares two scales of texture per region:
- fine detail: the deviation of luminance minus a 5 px blur;
- panel-scale mottling: a 5 px blur minus a 25 px blur.

Too low means "too clean, CG". It caught the smooth-concrete look that the user later named ("needs a
rougher texture"). Run it at stage 6.

For repeating ground patterns, measure the period by autocorrelation along image rows (`tools/ground_period.py`)
and convert it to millimetres with `cam.py`. Take the palette from k-means clusters of photo regions in
sun and in shade (`tools/ground_palette.py`), not from one picked pixel.

### 4.4 Fitted geometry
- **Shapes by least squares.** Click the visible corners or edge points of a regular shape in the photo,
  then solve its parameters (centre, radius, rotation, heights) by least squares through `cam.project`
  (`tools/fountain_fit.py` for the octagonal basin). This is far steadier than placing from one ground point.
- **Lines snapped to edges.** `tools/facade_linefit.py` fits a guessed eave, floor or ridge line to the
  strongest nearby horizontal edge, with a dark-to-bright sign option.
- **Height profiles.** `tools/facade_vprof.py` prints photo and render luminance row by row in a strip. A
  floor line or slab edge that is a few pixels off shows as a shifted step.

### 4.5 Placement from photo pixels
Organic and furniture domains write their specs in photo pixels: a foot point, the top of the head, the
side used for width. `tools/life_place.py` then raycasts them through the solved camera onto the ground or
the wall planes from the layout, writing world placements under `placed`. A person or chair is then
exactly where the photo has it, and re-measuring means changing a pixel.

### 4.6 Region checks and difference maps
- **Fixed regions per domain.** Each domain keeps a fixed table of photo boxes and a script that prints
  photo against render per box (`facade_regcmp.py`, `fountain_regions.py`, `ground_stats.py`). The same
  boxes every round make progress comparable. Report the numbers in the final report.
- **Difference maps.** `tools/light_diffmap.py` (blurred luminance difference, with a grid) and
  `light_shadecmp.py` (smoothed log2 ratio) colour the render red where it is too bright and blue where it
  is too dark. They show where a light error is, not just how large, and an off-camera shadow that is
  missing shows up immediately.

## 5. Film of a reconstruction (after fidelity and mood approval)
The user's rules from both runs:
- **Never show beyond the modelled area.** The model is built for one camera, so zoomed-out views
  reveal the gaps. Keep every film camera at eye level, framed inside the reconstructed square.
- **Flatten the ground for moving shots** (a film mood overlay: world-space grid, displacement 0, cobbles
  as bump only). Displacement that reads fine from the solved camera shows bumps and cut-offs in motion.
- **Fade the cloud dome as the camera rises.** Low clouds smear into streaks above the roofs; in clay view,
  fade them fully.
- Two views at most, each with an explicit meaning, for example clay for light and form and agent colours
  for who built what.
- A calm edit: no big captions, blur or pixel glitches, zoom punches or rapid cuts between scenes, and
  neutral music. Keep the 4:5 Instagram format.
- Render film frames in short chunks in fresh Blender processes with retries
  (`tools/film_render.sh`), because long runs hit CUDA illegal-address errors.

## 6. Cautions
- **Photo-derived textures stay in the reconstruction.** Agents may crop flat artwork from the photo as
  decals (`tools/facade_decals.py`: a mural behind glass, a carved door). If the scene is later shipped or
  sold, replace those decals and any branding with original art, and never ship the reference photo or
  crops of it.
- **Disk.** Blender processes grow the Windows pagefile, which reached 53 GB and filled C: on both runs.
  Before a wave, check free space; after a film or pass, delete frame dumps once the video is encoded.

## 7. Code-generated architecture (November 2026)
The user asked for buildings "generated purely in code ... beyond primitive geometries". Three worlds
(a city junction, a tiled corner shop, a cliffside pump station) were built by 10 domain agents with
the same harness as above, but with the approved concept aerial as the target
(`ref/photo.jpg`) and the user's reference as a style board only. Each agent kept a technique log and naive
vs code-generated A/B crops of the same view (34 images in all). What the evidence showed, best first.

Technique ids: T1 profile sweeps and lofts, T2 Geometry Nodes instancing built from Python, T3 SDF / volume
modelling, T4 subdivision cages, T5 curve-driven facade systems, T6 instanced detail kits, T7 generated height
maps and displacement, T8 bakeable shader weathering.

| technique | where it won | evidence |
|---|---|---|
| Profile sweeps / lathes in bmesh (T1): one 2D section swept along a path | balcony bands with drip grooves (~3k tris for five bands), kerbs and the red loop, spillway lofts, pipes with flanges, bollards, cornices, awnings, container corrugation; most detail per triangle everywhere | A/B crop |
| Instanced kits through a Python-built GN tree (T6/T2), realised before export | ~2,000 real bevelled mosaic tiles with per-tile colour/tilt, pergola slats/joists, bolts, railing posts, treads, pavers with settlement and cracked tiles | A/B crop |
| Curve-driven facade systems (T5) | ~140 aerofoil gold fins spaced by arc length, lofted through height stations with twist/depth variation on a least-squares-fitted rounded plan | A/B crop |
| Facade grammar from layout data | connected massings with bays, balconies, windows and shop units per floor (never boxes); storey height MEASURED from the target (a vertical luminance profile found 4.0 m; the guess was 1.8 m off) | A/B crop |
| Subdivision cages from code (T4) | rounded white modules: every radius from the layout, crisp reveals, 4 s builds; signal heads (a Subsurf modifier, not bmesh smooth-subdivide, which made blobs) | A/B crop |
| SDF / volume modelling (T3) | only at concave junctions (modules flowing into the deck); worse elsewhere (one global radius, reveals softened to the voxel size, 2.3x tris). Best combo: T4 modules + an SDF pass for junctions only | A/B crop |
| Volume terrain: numpy density field + own surface-nets mesher, profiles measured from the target, erosion, columnar basalt, strata | the pump-station cliff, far better than a displaced plane (flat, holes) | A/B crop |
| Code-grown plants | a swept palm with ring scars and drawn alpha leaflets beat the paid Meshy palm (a broadleaf blob); street trees grown as branch skeletons dressed with real Poly Haven leaf twigs beat the mesh-bank trees | A/B crop |
| Cloth simulation from code | the shop banner gets real folds and a sagging corner; a flat plane reads as a signboard | A/B crop |
| Generated height maps (T7) | brick coursing colour/relief (brick matched the target within ~3 levels) | A/B crop |
| Weak or wasted | displacement for the mosaic (3x tris, softer grout); true I-beam profiles and GN grating bars (sub-pixel at aerial range: lacing/silhouette matters, not the section); a site-wide wear map (invisible from the air); wall-wide streak atlases (read as corrugation; keep streaks under sills) | technique logs |

Rules that came out of it:
- **Measure before modelling**, as for photos: least-squares fits (tower plan, kerb fillet r 2.85 m), an
  orthophoto of the target projected onto the ground, vertical luminance
  profiles for floor lines. The concept is an AI image and not consistent; match mid-face and say so.
- **Silhouette detail beats section detail** at aerial range: put triangles into profiles, setbacks, fins and
  overhangs, not into bolts and I-beam flanges (keep those on separate `<DOMAIN>_DETAIL_*` objects so a light export can drop them).
- **Shader weathering must be bakeable and density-aware.** Per-object atlases of generated meshes fragment
  (panel grooves and kits make thousands of islands, 13-26 % texture use): join per domain, chunk large
  objects, repack tightly, and turn attribute-driven terrain into a few zoned tileable materials (rock /
  moss / wet band) with box UVs before exporting to a game engine.
- **Generated heavy props** (image-to-3D vehicles) are still the right call for vehicles and machines; code wins for
  architecture, infrastructure and, surprisingly, palms and trees.
- **Never bake hero LODs while agents render** (`bake_lods.py` held the GPU lock ~30 min), and cap any loop that
  allocates: a runaway atlas chunk-splitter grew the pagefile to 83.5 GB and left C: with 1.4 GB (reboot fixed it).
- Name regexes on prefixed object names: `tree` matches `STREET`. Match whole words after the prefix.

## What is and is not established
- **Tram run:** the user approved v1 fidelity by eye, at a region colour score of 10.1.
- **Fischbrunnen:** the score went from 4.8 to 4.0 over five rounds, with the light check best at 1.5.
  The user judged each round by eye, and the measured-light and sensor rounds answered their notes.

There was no controlled comparison against the older single-agent method on the same photo. The relative
weight of each practice here is judgement, not measurement.
