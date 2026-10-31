#!/usr/bin/env python3
"""Rebuild clean Schaffernak GLB: original exterior + V3 interiors, no V4/V5.
Requires Python standard library only. Does not silently replace windows.
"""
import argparse, json, re, struct
from pathlib import Path
from collections import Counter

def read_glb(path):
    raw=Path(path).read_bytes()
    magic,ver,length=struct.unpack_from("<III",raw)
    if (magic,ver,length)!=(0x46546c67,2,len(raw)): raise ValueError("Invalid GLB")
    at=12; chunks={}
    while at<len(raw):
        n,kind=struct.unpack_from("<II",raw,at);at+=8
        chunks[kind]=raw[at:at+n];at+=n
    return json.loads(chunks[0x4e4f534a]),chunks[0x004e4942]

def save(path,doc,blob):
    blob.extend(b"\0"*(-len(blob)%4))
    doc["buffers"]=[{"byteLength":len(blob)}]
    j=json.dumps(doc,separators=(",",":")).encode()
    j+=b" "*(-len(j)%4)
    out=struct.pack("<III",0x46546c67,2,12+8+len(j)+8+len(blob))
    out+=struct.pack("<II",len(j),0x4e4f534a)+j
    out+=struct.pack("<II",len(blob),0x004e4942)+blob
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_bytes(out)

def build(master_path,interior_path,output):
    items=json.loads(Path(master_path).read_text(encoding="utf8"))
    groups=Counter(o["group"] for o in items)
    required={"Beton","Ueberdachung","Carport","Holz","Metall","Edelstahl","Glas","Gelaende"}
    names=[o["name"] for o in items]
    if len(items)<600 or not required.issubset(groups) or len(names)!=len(set(names)):
        raise ValueError("Original master incomplete or contains duplicate mesh names")
    doc={"asset":{"version":"2.0","generator":"Schaffernak clean rebuild"},
         "scene":0,"scenes":[{"nodes":[]}],"nodes":[],"meshes":[],
         "materials":[],"bufferViews":[],"accessors":[],"buffers":[]}
    blob=bytearray(); mats={}
    def accessor(raw,component,typ,count,bounds=None,target=34962):
        blob.extend(b"\0"*(-len(blob)%4))
        offset=len(blob);blob.extend(raw)
        view=len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer":0,"byteOffset":offset,"byteLength":len(raw),"target":target})
        a={"bufferView":view,"componentType":component,"count":count,"type":typ}
        if bounds is not None:a["min"],a["max"]=bounds
        idx=len(doc["accessors"]);doc["accessors"].append(a);return idx
    for o in items:
        vertices=[(float(x),float(z),-float(y)) for x,y,z in o["v"]]
        faces=[int(i) for face in o["f"] for i in face]
        if not vertices or not faces or len(faces)%3:raise ValueError("Bad master mesh "+o["name"])
        flat=[v for p in vertices for v in p]
        pos=accessor(struct.pack("<"+"f"*len(flat),*flat),5126,"VEC3",len(vertices),
            ([min(p[i] for p in vertices) for i in range(3)],
             [max(p[i] for p in vertices) for i in range(3)]))
        idx=accessor(struct.pack("<"+"I"*len(faces),*faces),5125,"SCALAR",len(faces),target=34963)
        group,color=o["group"],o["c"];key=(group,color)
        if key not in mats:
            rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
            glass=group in ("Glas","Glasfolie")
            mat={"name":group+"_"+color,"doubleSided":True,
                 "pbrMetallicRoughness":{"baseColorFactor":rgb+[0.12 if group=="Glas" else 0.025 if group=="Glasfolie" else 1],
                 "metallicFactor":1 if group=="Edelstahl" else 0,
                 "roughnessFactor":0.35 if group=="Edelstahl" else 0.1 if glass else 0.8}}
            if glass:mat["alphaMode"]="BLEND"
            mats[key]=len(doc["materials"]);doc["materials"].append(mat)
        mesh=len(doc["meshes"])
        doc["meshes"].append({"name":o["name"],"primitives":[{"attributes":{"POSITION":pos},
                              "indices":idx,"material":mats[key]}]})
        node=len(doc["nodes"])
        doc["nodes"].append({"name":o["name"],"mesh":mesh})
        doc["scenes"][0]["nodes"].append(node)

    v3,source=read_glb(interior_path)
    if len(v3.get("buffers",[]))!=1:raise ValueError("Expected one V3 binary buffer")
    parents={}
    for i,n in enumerate(v3["nodes"]):
        for c in n.get("children",[]):parents[c]=i
    selected=[(i,n) for i,n in enumerate(v3["nodes"]) if "mesh" in n and
              (n.get("name","").startswith("Innen__") or re.match(r"^(EG|OG)_Kamin_",n.get("name","")))]
    if not selected:raise ValueError("V3 interior meshes not found; no output created")
    chosen=[n["name"] for _,n in selected]
    if len(chosen)!=len(set(chosen)) or set(chosen)&set(names):
        raise ValueError("Duplicate or colliding interior mesh names")
    for i,n in selected:
        parent=parents.get(i)
        while parent is not None:
            ancestor=v3["nodes"][parent]
            if any(k in ancestor for k in ("translation","rotation","scale","matrix")):
                raise ValueError("V3 has transformed parent; unsafe alignment")
            parent=parents.get(parent)
        if any(k in n for k in ("skin","children")):
            raise ValueError("Unsupported skinned or grouped interior mesh")
    viewmap={};accmap={};matmap={};meshmap={}
    def view(i):
        if i not in viewmap:
            old=v3["bufferViews"][i];start=old.get("byteOffset",0)
            blob.extend(b"\0"*(-len(blob)%4))
            new={**old,"buffer":0,"byteOffset":len(blob)}
            blob.extend(source[start:start+old["byteLength"]])
            viewmap[i]=len(doc["bufferViews"]);doc["bufferViews"].append(new)
        return viewmap[i]
    def acc(i):
        if i not in accmap:
            a=dict(v3["accessors"][i])
            if "sparse" in a:raise ValueError("Sparse V3 accessor not supported")
            if "bufferView" in a:a["bufferView"]=view(a["bufferView"])
            accmap[i]=len(doc["accessors"]);doc["accessors"].append(a)
        return accmap[i]
    def mat(i):
        if i not in matmap:
            m=dict(v3["materials"][i])
            if "Texture" in json.dumps(m):raise ValueError("V3 interior texture needs manual merge")
            matmap[i]=len(doc["materials"]);doc["materials"].append(m)
        return matmap[i]
    def mesh(i):
        if i not in meshmap:
            m=dict(v3["meshes"][i]);prims=[]
            for original in m["primitives"]:
                p=dict(original)
                p["attributes"]={k:acc(v) for k,v in p["attributes"].items()}
                if "indices" in p:p["indices"]=acc(p["indices"])
                if "material" in p:p["material"]=mat(p["material"])
                if "targets" in p:p["targets"]=[{k:acc(v) for k,v in t.items()} for t in p["targets"]]
                prims.append(p)
            m["primitives"]=prims
            meshmap[i]=len(doc["meshes"]);doc["meshes"].append(m)
        return meshmap[i]
    for _,n in selected:
        node={k:v for k,v in n.items() if k not in ("children","skin","camera")}
        node["mesh"]=mesh(n["mesh"])
        i=len(doc["nodes"]);doc["nodes"].append(node);doc["scenes"][0]["nodes"].append(i)
    save(output,doc,blob)
    report={"exterior_source":str(master_path),"interior_source":str(interior_path),
            "exterior_meshes":len(items),"interior_meshes":len(selected),
            "groups":dict(groups),"duplicate_names":0,
            "window_policy":"Original exterior windows preserved; V3 window changes pending separate verification.",
            "source_policy":"No V4/V5 and no V3 exterior geometry used."}
    Path(str(output)+".report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
    print(f"OK: {len(items)} original exterior + {len(selected)} V3 interior meshes = {len(doc['nodes'])} total")
    print("Report:",str(output)+".report.json")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--exterior",required=True,type=Path)
    p.add_argument("--interior",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();build(a.exterior,a.interior,a.output)
