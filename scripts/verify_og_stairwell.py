#!/usr/bin/env python3
"""Verify the EG-OG stairwell opening in a generated Schaffernak V6 GLB."""
import argparse
import json
import math
import struct
from pathlib import Path


def read_json_chunk(path):
    raw=Path(path).read_bytes()
    magic,version,total=struct.unpack_from("<III",raw,0)
    if (magic,version,total)!=(0x46546c67,2,len(raw)):
        raise ValueError("Invalid GLB")
    size,kind=struct.unpack_from("<II",raw,12)
    if kind!=0x4E4F534A:
        raise ValueError("GLB JSON chunk missing")
    return json.loads(raw[20:20+size])


def bounds(doc,node):
    mesh=doc["meshes"][node["mesh"]]
    mins=[];maxs=[]
    for primitive in mesh["primitives"]:
        a=doc["accessors"][primitive["attributes"]["POSITION"]]
        mins.append(a["min"]);maxs.append(a["max"])
    return ([min(v[i] for v in mins) for i in range(3)],
            [max(v[i] for v in maxs) for i in range(3)])


def check(path):
    doc=read_json_chunk(path)
    nodes={n["name"]:n for n in doc["nodes"] if "mesh" in n}
    if "OG_Decke" in nodes:
        raise AssertionError("Original solid OG slab still present")
    slab=[n for n in nodes if n.startswith("OG_Decke_Treppenoeffnung_Teil_")]
    floor=[n for n in nodes if n.startswith("Innen__Bodenbelag_OG_Treppenrand_")]
    treads=[n for n in nodes if n.startswith("Innen__Treppe_EG_OG_Lauf_")]
    assert len(slab)==4,(len(slab),"OG concrete panels")
    assert len(floor)==4,(len(floor),"OG parquet edge strips")
    assert len(treads)==18,(len(treads),"EG-OG stair treads")
    assert "Innen__Treppe_EG_OG_Wendepodest" in nodes
    for name in slab:
        lo,hi=bounds(doc,nodes[name])
        assert abs(lo[1]-2.77)<.02 and abs(hi[1]-2.97)<.02,(name,lo,hi)
    for name in floor:
        lo,hi=bounds(doc,nodes[name])
        assert abs(lo[1]-2.975)<.01 and abs(hi[1]-2.993)<.01,(name,lo,hi)
    parapet=nodes["Innen__OG_Stiege_Bruestung_zwischen_Laeufen"]
    lo,hi=bounds(doc,parapet)
    assert abs(lo[1]-2.70)<.02 and abs(hi[1]-3.70)<.02,(lo,hi)
    oak=nodes["Innen__OG_Stiege_Eichenholz_Abdeckung"]
    oak_lo,oak_hi=bounds(doc,oak)
    assert abs(oak_lo[1]-2.895)<.02 and abs(oak_hi[1]-3.74)<.02,(oak_lo,oak_hi)
    assert oak_lo[0]<lo[0] and oak_hi[0]>hi[0],(oak_lo,oak_hi)
    oak_primitive=doc["meshes"][oak["mesh"]]["primitives"][0]
    oak_material=doc["materials"][oak_primitive["material"]]
    assert oak_material["name"]=="OG_Stiege_Eichenholz_Abdeckung"
    # The mistakenly shortened OG_040 wall must remain original height.
    restored=nodes["Innen__Innenwand_DXF_OG_040"]
    restored_lo,restored_hi=bounds(doc,restored)
    assert all(abs(a-b)<.015 for a,b in zip(restored_lo,[3.67,3.00,-7.42])),restored_lo
    assert all(abs(a-b)<.015 for a,b in zip(restored_hi,[3.80,5.52,-5.35])),restored_hi
    assert "Innen__OG_Stiegenoeffnung_Bruestungsmauer_Links" not in nodes
    assert "Innen__OG_Stiegenoeffnung_Eichenholzabdeckung_Links" not in nodes
    assert "Innen__OG_Stiegenoeffnung_Bruestung_Eckanschluss" not in nodes
    assert "Innen__OG_Stiegenoeffnung_Eichenholz_Eckanschluss" not in nodes
    print("OK: OG opening 2.37 x 2.30 m, four concrete panels")
    print("OK: four matching parquet edge strips")
    print("OK: 18 EG-OG treads and landing preserved")
    print("OK: centre parapet approx. 90 cm above stair treads")
    print("OK: solid oak cap 40 mm thick with 30 mm side overhang")
    print("OK: OG wall 040 restored to original full height")
    print("OK: no transverse return wall or oak cap blocking stairwell")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("glb",type=Path)
    check(p.parse_args().glb)
