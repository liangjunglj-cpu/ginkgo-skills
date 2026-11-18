# ginkgo-skills

Agent skills from the Ginkgo project, shared for anyone to read and use.

## photo-scene-reconstruction

`skills/photo-scene-reconstruction/SKILL.md` teaches an AI coding agent (written for Claude Code) to rebuild a
reference photo or concept image as a Blender scene that holds up side by side with the original, using:

- a multi-agent harness: one lead plus 4-6 domain agents, each owning one module and one layout file;
- a frozen, solved camera and a render-and-compare loop (overlay, edge and crop sheets after every change);
- a fixed fidelity order (read, silhouette, proportion, colour, small parts, wear) with gates;
- light and materials measured from the image instead of tuned by eye;
- a real-mesh rule for organic and object-like things (no primitive stand-ins);
- a ranked list of code-generation techniques for detailed, organic architecture (section 7): profile sweeps,
  Geometry Nodes kits, curve-driven facades, facade grammars, subdivision cages, SDF blends, volume terrain,
  code-grown plants, with what worked and what did not.

`skills/photo-scene-reconstruction/harness/` holds the generic run scaffold: `blender/build_scene.py`
(orchestrator), `render.py`, `light.py`, `lib.py`, `assets.py`, and `tools/` (`cam.py` camera model,
`vp3.py` vanishing-point solver, `iterate.sh` build-render-compare loop, overlay/edge/crop/stats tools,
Poly Haven fetchers). Copy `blender/` and `tools/` into a run folder, add `ref/photo.jpg`,
`layout/camera.json`, `layout/order.json` and one `cg_<domain>.py` module per domain.

### Install

Copy `skills/photo-scene-reconstruction` into your project's `.claude/skills/` (or `~/.claude/skills/`).

Requirements: Blender 5.x (Cycles), Python with numpy, opencv-python and pillow for the 2D tools
(`tools/py.sh` uses `uv`), and Git Bash or another POSIX shell for `iterate.sh`.

## License

MIT, see `LICENSE`.
