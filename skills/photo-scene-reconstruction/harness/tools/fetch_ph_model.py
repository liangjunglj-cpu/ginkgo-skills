"""Download CC0 Poly Haven models (glTF 2k + textures) into gen/ph/<id>/."""
import json, sys, urllib.request, pathlib
OUT = pathlib.Path(__file__).resolve().parents[1] / "gen" / "ph"
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ginkgo-scene/1.0"}), timeout=300).read()
for aid in sys.argv[1:]:
    f = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))["gltf"]["2k"]["gltf"]
    d = OUT / aid; d.mkdir(parents=True, exist_ok=True)
    (d / f["url"].rsplit("/", 1)[-1]).write_bytes(get(f["url"]))
    for rel, inc in f.get("include", {}).items():
        p = d / rel; p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists(): p.write_bytes(get(inc["url"]))
    print(aid, sum(1 for _ in d.rglob("*")), "files")
