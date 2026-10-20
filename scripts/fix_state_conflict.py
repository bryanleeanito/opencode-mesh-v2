#!/usr/bin/env python3
# fix_broadcasts_conflict.py — resolver conflict git pada state/broadcasts.json
# Masalah: sync.py --pull melakukan merge git; jika 2 mesin sama2 ubah file
# state yang sama -> conflict marker tertanam di JSON -> file rusak (JSON invalid)
# -> broadcast.py crash. Script ini menggabungkan kedua sisi tanpa duplikat.
import json
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "state/broadcasts.json"

with open(PATH, encoding="utf-8") as f:
    raw = f.read()

if "<<<<<<<" not in raw:
    print("[i] tidak ada conflict marker — file bersih")
    sys.exit(0)

lines = raw.split("\n")
ours, theirs, cur = [], [], None
for ln in lines:
    if ln.startswith("<<<<<<<"):
        cur = "ours"
        continue
    if ln.startswith("======="):
        cur = "theirs"
        continue
    if ln.startswith(">>>>>>>"):
        cur = None
        continue
    if cur == "ours":
        ours.append(ln)
    elif cur == "theirs":
        theirs.append(ln)


def parse(block):
    txt = "\n".join(block).strip()
    # buang sisa penanda & ambil array JSON pertama yang valid
    txt = re.sub(r"^>>>>>>>.*$", "", txt, flags=re.M).strip()
    try:
        return json.loads(txt)
    except Exception:
        # coba ambil dari '[' pertama sampai ']' terakhir
        i, j = txt.find("["), txt.rfind("]")
        if i == -1 or j == -1:
            return None
        try:
            return json.loads(txt[i : j + 1])
        except Exception as e:
            print("[!] parse gagal:", e)
            return None


a = parse(ours) or []
b = parse(theirs) or []
print(f"[i] sisi HEAD={len(a)} item, sisi remote={len(b)} item")

seen, merged = set(), []
for item in a + b:
    if not isinstance(item, dict):
        continue
    k = item.get("id") or json.dumps(item, sort_keys=True)[:120]
    if k in seen:
        continue
    seen.add(k)
    merged.append(item)

merged.sort(key=lambda x: x.get("created", ""))

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"[+] conflict resolved -> {PATH} ({len(merged)} item unik)")
