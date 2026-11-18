"""Download CC0 Poly Haven texture sets (2k jpg) into runs/freiburg_tram/tex/<id>/."""
import json, sys, urllib.request, pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "tex"
MAPS = {"Diffuse": "diff", "nor_gl": "nor_gl", "Rough": "rough", "Displacement": "disp", "AO": "ao", "arm": "arm"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ginkgo-scene/1.0"})
    return urllib.request.urlopen(req, timeout=120).read()

for aid in sys.argv[1:]:
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}").decode("utf-8"))
    d = OUT / aid
    d.mkdir(parents=True, exist_ok=True)
    for key, short in MAPS.items():
        try:
            f = files[key]["2k"]["jpg"] if key != "Displacement" else files[key]["2k"].get("jpg") or files[key]["2k"]["png"]
        except KeyError:
            continue
        ext = f["url"].rsplit(".", 1)[-1]
        p = d / f"{aid}_{short}_2k.{ext}"
        if not p.exists():
            p.write_bytes(get(f["url"]))
    print(aid, sorted(x.name for x in d.iterdir()))
