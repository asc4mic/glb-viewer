#!/usr/bin/env python3
"""Rebuild clean Schaffernak GLB: original exterior + V3 interiors, no V4/V5.
Requires Python standard library only. Does not silently replace windows.
"""
import argparse, json, re, struct
from pathlib import Path
from collections import Counter
from balcony_glass_on_slab import replace_glass_railing

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

def restore_og_right_gable_floor_windows(items):
    """Restore the two right-gable OG windows to floor height.

    Front-facing view of the right gable: near-front window = Stefan's room
    (OG_right_Glas1), farther window = bathroom (OG_right_Glas0).
    Original exterior coordinates are (x, depth, elevation); slab top z=2.97.
    No modifications to left gable, front windows, slab, or roof.
    """
    import copy
    items=copy.deepcopy(items)
    byname={}
    for o in items:
        byname.setdefault(o["name"],[]).append(o)
    expected={
        0:{"sill":3.97,"under":"OG_right_unten3","depth":(4.8253,5.8853)},
        1:{"sill":3.97,"under":"OG_right_unten1","depth":(0.50012,1.56012)},
    }
    floor=2.97
    for i,config in expected.items():
        glassname=f"OG_right_Glas{i}"
        glass=byname.get(glassname,[])
        under=byname.get(config["under"],[])
        if len(glass)!=1 or len(under)!=1:
            raise ValueError("Missing right OG gable glass or sill: "+glassname)
        sill=config["sill"]
        for o in (glass[0],under[0]):
            zmin=min(v[2] for v in o["v"])
            zmax=max(v[2] for v in o["v"])
            ymin=min(v[1] for v in o["v"])
            ymax=max(v[1] for v in o["v"])
            if (abs(zmin-(sill if o is glass[0] else floor))>0.015 or
                abs(ymin-config["depth"][0])>0.015 or
                abs(ymax-config["depth"][1])>0.015 or
                (o is under[0] and abs(zmax-sill)>0.015)):
                raise ValueError("Right OG gable geometry changed: "+o["name"])
        frames=[o for o in items if o["name"].startswith(f"OG_right_Rahmen{i}_")]
        if len(frames)!=4:
            raise ValueError("Expected 4 right OG window frame segments: "+glassname)
        bottom=[o for o in frames if
                abs(min(v[2] for v in o["v"])-sill)<0.015 and
                abs(max(v[2] for v in o["v"])-(sill+0.065))<0.015]
        if len(bottom)!=1:raise ValueError("Expected one bottom frame: "+glassname)
        items.remove(under[0])
        # Extend glass and both upright frame pieces to slab top.
        for o in [glass[0]]+[f for f in frames if f is not bottom[0]]:
            lo=min(v[2] for v in o["v"])
            hi=max(v[2] for v in o["v"])
            if abs(lo-sill)<0.015 and hi>sill+0.10:
                o["v"]=[[x,y,floor if abs(z-sill)<0.015 else z]
                        for x,y,z in o["v"]]
        # Move the existing bottom frame down rather than duplicating it.
        bottom[0]["v"]=[[x,y,z+floor-sill] for x,y,z in bottom[0]["v"]]
    return items


def build(master_path,interior_path,output):
    items=json.loads(Path(master_path).read_text(encoding="utf8"))
    groups=Counter(o["group"] for o in items)
    required={"Beton","Ueberdachung","Carport","Holz","Metall","Edelstahl","Glas","Gelaende"}
    names=[o["name"] for o in items]
    if len(items)<600 or not required.issubset(groups):
        raise ValueError("Original master incomplete or missing required exterior groups")
    items=restore_og_right_gable_floor_windows(items)
    items, railing_report=replace_glass_railing(items)
    names=[o["name"] for o in items]
    groups=Counter(o["group"] for o in items)
    name_counts=Counter(names)
    repeated={name:count for name,count in name_counts.items() if count>1}
    seen=Counter()
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
        # Same-name frame segments are separate geometry. Preserve them all.
        original_name=o["name"]
        seen[original_name]+=1
        export_name=(original_name if name_counts[original_name]==1 else
                     f"{original_name}__Teil_{seen[original_name]}")
        vertices=[(float(x),float(z),-float(y)) for x,y,z in o["v"]]
        faces=[int(i) for face in o["f"] for i in face]
        if not vertices or not faces or len(faces)%3:raise ValueError("Bad master mesh "+original_name)
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
        doc["meshes"].append({"name":export_name,"primitives":[{"attributes":{"POSITION":pos},
                              "indices":idx,"material":mats[key]}]})
        node=len(doc["nodes"])
        doc["nodes"].append({"name":export_name,"mesh":mesh})
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
            if ancestor.get("translation", [0,0,0]) != [0,0,0] or ancestor.get("rotation", [0,0,0,1]) != [0,0,0,1] or ancestor.get("scale", [1,1,1]) != [1,1,1] or ancestor.get("matrix", [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]) != [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]:
                raise ValueError("V3 has non-identity parent transform; unsafe alignment")
            parent=parents.get(parent)
        if any(k in n for k in ("skin","children")):
            raise ValueError("Unsupported skinned or grouped interior mesh")
    viewmap={};accmap={};matmap={};meshmap={}
    # Uniform porcelain-white finish for interior walls, not floors or stairs.
    wall_white_material=len(doc["materials"])
    doc["materials"].append({"name":"Innenwand_Porzellanweiss","doubleSided":True,
        "pbrMetallicRoughness":{"baseColorFactor":[0.97,0.965,0.95,1.0],
                               "metallicFactor":0,"roughnessFactor":0.9}})
    def is_interior_wall(name):
        return (name.startswith("Innen__") and
                ("Innenwand" in name or "_Wand_" in name or
                 "_Sturz" in name or "_Bruestung" in name))
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
    def mesh(i, white_wall=False):
        # Distinct mesh keys prevent changing a material shared with a floor.
        key=(i,white_wall)
        if key not in meshmap:
            m=dict(v3["meshes"][i]);prims=[]
            for original in m["primitives"]:
                p=dict(original)
                p["attributes"]={k:acc(v) for k,v in p["attributes"].items()}
                if "indices" in p:p["indices"]=acc(p["indices"])
                if white_wall:
                    p["material"]=wall_white_material
                elif "material" in p:
                    p["material"]=mat(p["material"])
                if "targets" in p:p["targets"]=[{k:acc(v) for k,v in t.items()} for t in p["targets"]]
                prims.append(p)
            m["primitives"]=prims
            meshmap[key]=len(doc["meshes"]);doc["meshes"].append(m)
        return meshmap[key]
    # Reverse EG->OG stair start side by reflecting only the two stair flights
    # about the midpoint of their shared opening (X=4.97 m).
    # This swaps A and B horizontally without changing any tread height,
    # stair pitch, opening, landing elevation, or neighboring walls.
    # The symmetric landing does not need to be reflected.
    stair_steps=[n for _,n in selected if re.fullmatch(
        r"Innen__Treppe_EG_OG_Lauf_[AB]_Stufe_[0-9]+",n["name"])]
    if len(stair_steps)!=18 or len([n for _,n in selected if
            n["name"]=="Innen__Treppe_EG_OG_Wendepodest"])!=1:
        raise ValueError("Expected 18 EG-OG treads and one landing; stair unchanged")
    for n in stair_steps:
        if any(k in n for k in ("matrix","translation","rotation","scale")):
            raise ValueError("Unexpected EG-OG tread transform; stair unchanged")
        primitive=v3["meshes"][n["mesh"]]["primitives"]
        if len(primitive)!=1:raise ValueError("Unexpected stair tread primitives")
        a=v3["accessors"][primitive[0]["attributes"]["POSITION"]]
        lo,hi=a["min"],a["max"]
        if not (3.83<=lo[0]<=5.19 and 4.75<=hi[0]<=6.11 and
                -6.90<=lo[2]<-5.17 and -6.90<hi[2]<=-5.17):
            raise ValueError("EG-OG stair footprint changed; stair unchanged")
    stair_partition_names={"Innen__Innenwand_DXF_OG_041","Innen__Innenwand_DXF_OG_026"}
    if not stair_partition_names.issubset(set(chosen)):
        raise ValueError("OG stair partition walls not found; refusing partial modification")
    for _,n in selected:
        if n["name"] in stair_partition_names:
            continue  # replaced below with a low parapet; keep original V3 intact
        node={k:v for k,v in n.items() if k not in ("children","skin","camera")}
        node["mesh"]=mesh(n["mesh"],is_interior_wall(n["name"]))
        if n in stair_steps:
            # Reflection about X=4.97; three.js handles negative-scale winding.
            node["translation"]=[9.94,0.0,0.0]
            node["scale"]=[-1.0,1.0,1.0]
        i=len(doc["nodes"]);doc["nodes"].append(node);doc["scenes"][0]["nodes"].append(i)
    # OG central partition between stair flights A and B:
    # Original walls 041 and 026 reach the ceiling (Y=5.52).
    # Replace both by one low solid parapet, retaining their combined footprint.
    # Original stair treads and landings are imported unchanged.
    stair_bounds=[]
    for _,wall in selected:
        if wall["name"] not in stair_partition_names: continue
        if any(k in wall for k in ("matrix","rotation","translation","scale")):
            raise ValueError("Stair partition has a transform; manual review required")
        prims=v3["meshes"][wall["mesh"]]["primitives"]
        if len(prims)!=1: raise ValueError("Unexpected multi-primitive stair partition")
        a=v3["accessors"][prims[0]["attributes"]["POSITION"]]
        stair_bounds.append((a["min"],a["max"]))
    if len(stair_bounds)!=2: raise ValueError("Expected two stair partition segments")
    x0=min(lo[0] for lo,hi in stair_bounds)
    x1=max(hi[0] for lo,hi in stair_bounds)
    z0=min(lo[2] for lo,hi in stair_bounds)
    z1=max(hi[2] for lo,hi in stair_bounds)
    y0=min(lo[1] for lo,hi in stair_bounds)
    # Sloping parapet along stair flight B. At the upper end (z1)
    # it rises 1.00 m above the OG floor; toward the lower end (z0)
    # the top descends with the stair gradient. Preserve OG floor baseline.
    upper_top=4.00
    lower_top=3.00
    if not (4.84<x0<4.87 and 5.10<x1<5.13 and
            -6.46<z0<-6.42 and -5.40<z1<-5.36 and
            2.99<y0<3.01 and all(abs(hi[1]-5.52)<.02 for lo,hi in stair_bounds)):
        raise ValueError("OG stair partition footprint changed; refusing to alter geometry")
    verts=[(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
           (x0,lower_top,z0),(x1,lower_top,z0),
           (x1,upper_top,z1),(x0,upper_top,z1)]
    faces=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,
           1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
    flat=[v for vertex in verts for v in vertex]
    pos=accessor(struct.pack("<"+"f"*len(flat),*flat),5126,"VEC3",8,
                 ([x0,y0,z0],[x1,upper_top,z1]))
    inds=accessor(struct.pack("<"+"I"*len(faces),*faces),5125,"SCALAR",len(faces),target=34963)
    parapet_mat=len(doc["materials"])
    doc["materials"].append({"name":"OG_Stiege_Bruestung_massiv",
        "doubleSided":True,"pbrMetallicRoughness":{
            "baseColorFactor":[0.97,0.965,0.95,1.0],
            "metallicFactor":0,"roughnessFactor":0.9}})
    parapet_name="Innen__OG_Stiege_Bruestung_zwischen_Laeufen"
    mi=len(doc["meshes"])
    doc["meshes"].append({"name":parapet_name,"primitives":[
        {"attributes":{"POSITION":pos},"indices":inds,"material":parapet_mat,"mode":4}]})
    ni=len(doc["nodes"])
    doc["nodes"].append({"name":parapet_name,"mesh":mi})
    doc["scenes"][0]["nodes"].append(ni)
    # Plan-safe small KG wall junction: original V3 walls 017 and 002
    # leave a 19 mm horizontal gap where both wall boxes overlap.
    # Add one small infill, without touching openings, other floors or V3.
    gap_name="Innen__Innenwand_DXF_KG_Anschluss_003"
    if gap_name in chosen or gap_name in names:
        raise ValueError("KG junction correction name already exists")
    x0,x1=6.41,6.45
    y0,y1=-2.69,-0.24
    z0,z1=-7.41,-7.22
    verts=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
           (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    faces=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,
           1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
    flat=[v for vertex in verts for v in vertex]
    pos=accessor(struct.pack("<"+"f"*len(flat),*flat),5126,"VEC3",8,
                 ([x0,y0,z0],[x1,y1,z1]))
    inds=accessor(struct.pack("<"+"I"*len(faces),*faces),5125,"SCALAR",len(faces),target=34963)
    material=len(doc["materials"])
    doc["materials"].append({"name":"KG_Innenwand_Anschluss","doubleSided":True,
       "pbrMetallicRoughness":{"baseColorFactor":[0.97,0.965,0.95,1.0],
                              "metallicFactor":0,"roughnessFactor":0.9}})
    mi=len(doc["meshes"])
    doc["meshes"].append({"name":gap_name,"primitives":[{"attributes":{"POSITION":pos},
        "indices":inds,"material":material,"mode":4}]})
    ni=len(doc["nodes"])
    doc["nodes"].append({"name":gap_name,"mesh":mi})
    doc["scenes"][0]["nodes"].append(ni)
    # EG: one genuine 13 cm T-junction gap in the DXF wall network.
    # EG_011 ends at x=8.67, EG_012 begins at x=8.80, and EG_038
    # terminates at z=-5.25. Unlike the other reported gaps, no wall
    # occupies this 0.13 x 0.13 m footprint.
    eg_joint_name="Innen__Innenwand_DXF_EG_Anschluss_003"
    eg_expected={
        "Innen__Innenwand_DXF_EG_011":([8.18,0.03,-5.25],[8.67,2.70,-5.12]),
        "Innen__Innenwand_DXF_EG_012":([8.80,0.03,-5.25],[10.72,2.70,-5.12]),
        "Innen__Innenwand_DXF_EG_038":([8.67,0.03,-6.45],[8.80,2.70,-5.25]),
    }
    if eg_joint_name in chosen or eg_joint_name in names:
        raise ValueError("EG junction fix already present in source")
    for _,wall in selected:
        if wall["name"] not in eg_expected:continue
        if any(k in wall for k in ("matrix","translation","rotation","scale")):
            raise ValueError("EG junction source has transform")
        primitive=v3["meshes"][wall["mesh"]]["primitives"][0]
        a=v3["accessors"][primitive["attributes"]["POSITION"]]
        expected_lo,expected_hi=eg_expected.pop(wall["name"])
        if any(abs(a["min"][i]-expected_lo[i])>0.015 or
               abs(a["max"][i]-expected_hi[i])>0.015 for i in range(3)):
            raise ValueError("EG junction source bounds changed: "+wall["name"])
    if eg_expected:raise ValueError("Missing EG junction neighbors: "+str(list(eg_expected)))
    ex0,ex1=8.67,8.80
    ey0,ey1=0.03,2.70
    ez0,ez1=-5.25,-5.12
    # A full-height fill follows the adjacent RAW wall meshes. The
    # confirmed 2.50 m FINISHED clear height is not the raw mesh height.
    ev=[(ex0,ey0,ez0),(ex1,ey0,ez0),(ex1,ey0,ez1),(ex0,ey0,ez1),
        (ex0,ey1,ez0),(ex1,ey1,ez0),(ex1,ey1,ez1),(ex0,ey1,ez1)]
    ef=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,
        1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
    ep=accessor(struct.pack("<"+"f"*24,*[v for xyz in ev for v in xyz]),
                5126,"VEC3",8,([ex0,ey0,ez0],[ex1,ey1,ez1]))
    ei=accessor(struct.pack("<"+"I"*len(ef),*ef),5125,"SCALAR",len(ef),target=34963)
    em=len(doc["meshes"])
    doc["meshes"].append({"name":eg_joint_name,"primitives":[{
        "attributes":{"POSITION":ep},"indices":ei,"material":material,"mode":4}]})
    en=len(doc["nodes"])
    doc["nodes"].append({"name":eg_joint_name,"mesh":em})
    doc["scenes"][0]["nodes"].append(en)
    # OG: V3 door lintels stop at y=5.17 m while all adjacent OG walls
    # continue to y=5.52 m. Fill ONLY the six proven 35 cm top gaps.
    # Preserve the original door clear openings and lintels below.
    og_wall_tops=[]
    for _,wall in selected:
        if not re.fullmatch(r"Innen__Innenwand_DXF_OG_[0-9]+",wall["name"]):
            continue
        primitive=v3["meshes"][wall["mesh"]]["primitives"][0]
        a=v3["accessors"][primitive["attributes"]["POSITION"]]
        if "max" in a: og_wall_tops.append(a["max"][1])
    if len(og_wall_tops)<20 or max(og_wall_tops)-min(og_wall_tops)>0.01:
        raise ValueError("OG wall heights differ; do not fill door lintels automatically")
    og_wall_top=max(og_wall_tops)
    og_lintels=[n for _,n in selected if re.fullmatch(r"Innen__OG_Tuer_.*_Sturz",n["name"])]
    if len(og_lintels)!=6:
        raise ValueError(f"Expected six OG lintels; found {len(og_lintels)}")
    og_header_fixes=[]
    for lintel in og_lintels:
        primitive=v3["meshes"][lintel["mesh"]]["primitives"][0]
        bounds=v3["accessors"][primitive["attributes"]["POSITION"]]
        if "min" not in bounds or "max" not in bounds:
            raise ValueError("OG lintel has no position bounds")
        low,high=bounds["min"],bounds["max"]
        if not (0.25 < og_wall_top-high[1] < 0.45):
            raise ValueError("Unexpected OG gap over "+lintel["name"])
        if "matrix" in lintel or "translation" in lintel or "rotation" in lintel or "scale" in lintel:
            raise ValueError("OG lintel transform needs manual inspection")
        # Same horizontal footprint as the original lintel; continuous wall to 5.52 m.
        x0,z0=low[0],low[2]
        x1,z1=high[0],high[2]
        y0,y1=high[1],og_wall_top
        verts=[(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
               (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)]
        faces=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,
               1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
        flat=[value for vertex in verts for value in vertex]
        pos=accessor(struct.pack("<"+"f"*len(flat),*flat),5126,"VEC3",8,
                     ([x0,y0,z0],[x1,y1,z1]))
        inds=accessor(struct.pack("<"+"I"*len(faces),*faces),5125,"SCALAR",len(faces),target=34963)
        name=lintel["name"].replace("_Sturz","_Wand_oberhalb_Sturz")
        mi=len(doc["meshes"])
        doc["meshes"].append({"name":name,"primitives":[{"attributes":{"POSITION":pos},
            "indices":inds,"material":material,"mode":4}]})
        ni=len(doc["nodes"])
        doc["nodes"].append({"name":name,"mesh":mi})
        doc["scenes"][0]["nodes"].append(ni)
        og_header_fixes.append(name)
    # EG: V3 door lintels stop at y=2.20 m while all adjacent EG walls
    # continue to y=2.70 m. Fill ONLY the five proven 50 cm top gaps.
    # Preserve the original door clear openings and lintels below.
    eg_wall_tops=[]
    for _,wall in selected:
        if not re.fullmatch(r"Innen__Innenwand_DXF_EG_[0-9]+",wall["name"]):
            continue
        primitive=v3["meshes"][wall["mesh"]]["primitives"][0]
        a=v3["accessors"][primitive["attributes"]["POSITION"]]
        if "max" in a: eg_wall_tops.append(a["max"][1])
    if len(eg_wall_tops)<20 or max(eg_wall_tops)-min(eg_wall_tops)>0.01:
        raise ValueError("EG wall heights differ; do not fill door lintels automatically")
    eg_wall_top=max(eg_wall_tops)
    eg_lintels=[n for _,n in selected if re.fullmatch(r"Innen__EG_Tuer_.*_Sturz",n["name"])]
    if len(eg_lintels)!=5:
        raise ValueError(f"Expected five EG lintels; found {len(eg_lintels)}")
    eg_header_fixes=[]
    for lintel in eg_lintels:
        primitive=v3["meshes"][lintel["mesh"]]["primitives"][0]
        bounds=v3["accessors"][primitive["attributes"]["POSITION"]]
        if "min" not in bounds or "max" not in bounds:
            raise ValueError("EG lintel has no position bounds")
        low,high=bounds["min"],bounds["max"]
        if not (0.45 < eg_wall_top-high[1] < 0.55):
            raise ValueError("Unexpected EG gap over "+lintel["name"])
        if "matrix" in lintel or "translation" in lintel or "rotation" in lintel or "scale" in lintel:
            raise ValueError("EG lintel transform needs manual inspection")
        # Same horizontal footprint as the original lintel; continuous wall to 2.70 m.
        x0,z0=low[0],low[2]
        x1,z1=high[0],high[2]
        y0,y1=high[1],eg_wall_top
        verts=[(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
               (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)]
        faces=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,
               1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
        flat=[value for vertex in verts for value in vertex]
        pos=accessor(struct.pack("<"+"f"*len(flat),*flat),5126,"VEC3",8,
                     ([x0,y0,z0],[x1,y1,z1]))
        inds=accessor(struct.pack("<"+"I"*len(faces),*faces),5125,"SCALAR",len(faces),target=34963)
        name=lintel["name"].replace("_Sturz","_Wand_oberhalb_Sturz")
        mi=len(doc["meshes"])
        doc["meshes"].append({"name":name,"primitives":[{"attributes":{"POSITION":pos},
            "indices":inds,"material":material,"mode":4}]})
        ni=len(doc["nodes"])
        doc["nodes"].append({"name":name,"mesh":mi})
        doc["scenes"][0]["nodes"].append(ni)
        eg_header_fixes.append(name)
    save(output,doc,blob)
    report={"exterior_source":str(master_path),"interior_source":str(interior_path),
            "exterior_meshes":len(items),"interior_meshes":len(selected),
            "interior_wall_finish":"Porzellanweiss; named interior wall meshes, lintels and generated infills",
            "interior_junction_fixes":[gap_name,eg_joint_name],
            "og_stair_partition_replaced":sorted(stair_partition_names),
            "eg_og_stair_direction":"flights mirrored about X=4.97m; tread elevations unchanged",
            "og_stair_parapet":parapet_name,
            "og_stair_parapet_top_m":{"lower_end":lower_top,"upper_end":upper_top},
            "og_door_header_fixes":og_header_fixes,
            "eg_door_header_fixes":eg_header_fixes,
            "groups":dict(groups),"railing_update":railing_report,
            "original_repeated_names":repeated,
            "renamed_frame_parts":sum(repeated.values()),
            "window_policy":"Both right OG gable windows (Stefan and bathroom) extended to slab top z=2.97; left gable unchanged.",
            "source_policy":"No V4/V5 and no V3 exterior geometry used."}
    Path(str(output)+".report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf8")
    print(f"OK: {len(items)} original exterior + {len(selected)} V3 interior meshes = {len(doc['nodes'])} total")
    print("Preserved",sum(repeated.values()),"parts with repeated original names, uniquely renamed")
    print("Railing:",railing_report)
    print("Windows: right OG gable Stefan and bathroom windows restored to slab top z=2.97")
    print("Interior: wall surfaces, lintels and parapet in porcelain white")
    print("Interior: added KG wall junction fix",gap_name)
    print("Interior: added EG T-junction fix",eg_joint_name)
    print("Interior: OG stair partition replaced with sloped parapet",parapet_name)
    print("Interior: EG-OG stair flights mirrored; start side reversed (18 treads)")
    print("Interior: closed",len(og_header_fixes),"OG gaps above door lintels")
    print("Interior: closed",len(eg_header_fixes),"EG gaps above door lintels")
    print("Report:",str(output)+".report.json")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--exterior",required=True,type=Path)
    p.add_argument("--interior",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();build(a.exterior,a.interior,a.output)
