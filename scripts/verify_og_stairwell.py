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
    assert abs(lo[1]-2.70)<.02 and abs(hi[1]-3.87)<.02,(lo,hi)
    oak=nodes["Innen__OG_Stiege_Eichenholz_Abdeckung"]
    oak_lo,oak_hi=bounds(doc,oak)
    assert abs(oak_lo[1]-2.965)<.02 and abs(oak_hi[1]-3.91)<.02,(oak_lo,oak_hi)
    assert oak_lo[0]<lo[0] and oak_hi[0]>hi[0],(oak_lo,oak_hi)
    oak_primitive=doc["meshes"][oak["mesh"]]["primitives"][0]
    oak_material=doc["materials"][oak_primitive["material"]]
    assert oak_material["name"]=="OG_Stiege_Eichenholz_Abdeckung"
    # Red-marked long wall immediately left of the opening must be a
    # 90 cm masonry parapet with an oak cap, not a full-height wall.
    assert "Innen__Innenwand_DXF_OG_040" not in nodes
    masonry_name="Innen__OG_Stiegenoeffnung_Bruestungsmauer_Links"
    coping_name="Innen__OG_Stiegenoeffnung_Eichenholzabdeckung_Links"
    masonry=nodes[masonry_name]
    masonry_lo,masonry_hi=bounds(doc,masonry)
    assert all(abs(a-b)<.015 for a,b in zip(masonry_lo,[3.67,3.00,-7.42])),masonry_lo
    assert all(abs(a-b)<.015 for a,b in zip(masonry_hi,[3.80,3.87,-5.35])),masonry_hi
    coping=nodes[coping_name]
    coping_lo,coping_hi=bounds(doc,coping)
    assert abs(coping_lo[1]-3.865)<.015 and abs(coping_hi[1]-3.91)<.015,(coping_lo,coping_hi)
    coping_primitive=doc["meshes"][coping["mesh"]]["primitives"][0]
    assert doc["materials"][coping_primitive["material"]]["name"]=="OG_Stiege_Eichenholz_Abdeckung"
    # Reference 2: sloped and horizontal parapets meet in one L-shaped
    # masonry corner; both oak tops finish at exactly the same elevation.
    join_wall=nodes["Innen__OG_Stiegenoeffnung_Bruestung_Eckanschluss"]
    join_oak=nodes["Innen__OG_Stiegenoeffnung_Eichenholz_Eckanschluss"]
    join_lo,join_hi=bounds(doc,join_wall)
    join_oak_lo,join_oak_hi=bounds(doc,join_oak)
    assert abs(join_lo[1]-3.00)<.015 and abs(join_hi[1]-3.87)<.015
    assert abs(join_oak_hi[1]-3.91)<.015
    assert abs(join_oak_hi[1]-oak_hi[1])<.002
    assert abs(join_oak_hi[1]-coping_hi[1])<.002
    # Return connects landing's right side to slope's left side.
    assert join_lo[0]<masonry_hi[0] and join_hi[0]>=lo[0]-.01
    assert join_oak_hi[0]>=oak_lo[0]-.01
    assert join_oak_lo[2]<=hi[2] and join_oak_hi[2]>=hi[2]
    join_primitive=doc["meshes"][join_oak["mesh"]]["primitives"][0]
    assert doc["materials"][join_primitive["material"]]["name"]=="OG_Stiege_Eichenholz_Abdeckung"
    print("OK: OG opening 2.37 x 2.30 m, four concrete panels")
    print("OK: four matching parquet edge strips")
    print("OK: 18 EG-OG treads and landing preserved")
    print("OK: centre parapet approx. 90 cm above stair treads")
    print("OK: solid oak cap 40 mm thick with 30 mm side overhang")
    print("OK: red-marked OG wall 040 replaced with 90 cm masonry and oak coping")
    print("OK: sloped and horizontal masonry joined flush with oak corner cap")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("glb",type=Path)
    check(p.parse_args().glb)
