#!/usr/bin/env python3
"""Report OG interior wall and stair geometry from original V3 without modifying it."""
import argparse,struct,json,re
from pathlib import Path

def read_glb(path):
    raw=Path(path).read_bytes()
    magic,version,total=struct.unpack_from("<III",raw,0)
    if magic!=0x46546c67 or version!=2 or total!=len(raw):
        raise ValueError("Not a valid GLB")
    off=12; chunks={}
    while off<len(raw):
        size,kind=struct.unpack_from("<II",raw,off);off+=8
        chunks[kind]=raw[off:off+size];off+=size
    return json.loads(chunks[0x4e4f534a]),chunks[0x004e4942]

def bounds(doc,blob,mesh):
    boxes=[]
    for primitive in doc["meshes"][mesh]["primitives"]:
        a=doc["accessors"][primitive["attributes"]["POSITION"]]
        if "min" in a and "max" in a:
            boxes.append((a["min"],a["max"]))
        else:
            raise ValueError("Position accessor has no bounds")
    return ([min(b[0][i] for b in boxes) for i in range(3)],
            [max(b[1][i] for b in boxes) for i in range(3)])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("glb",type=Path)
    args=ap.parse_args()
    doc,blob=read_glb(args.glb)
    for node in doc["nodes"]:
        name=node.get("name","")
        if "mesh" not in node or not (
            name.startswith("Innen__Innenwand_DXF_OG_") or
            ("OG" in name and any(k in name.lower() for k in ("stiege","treppe","bruestung","brüstung","geländer","gelaender","tuer")))
        ):
            continue
        lo,hi=bounds(doc,blob,node["mesh"])
        if any(k in node for k in ("matrix","rotation","scale","translation")):
            print("TRANSFORM CHECK:",name,{k:node[k] for k in ("matrix","rotation","scale","translation") if k in node})
        print(f"{name:54} x={lo[0]:7.3f}..{hi[0]:7.3f}  height={lo[1]:7.3f}..{hi[1]:7.3f}  z={lo[2]:7.3f}..{hi[2]:7.3f}")
if __name__=="__main__":main()
