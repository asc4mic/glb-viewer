#!/usr/bin/env python3
"""Read-only audit of EG/OG wall joints in original Schaffernak V3 GLB.

All coordinates are glTF metres (Y vertical). No geometry is changed.
"""
import argparse
from inspect_og_stair import read_glb, bounds

def overlap(a,b): return max(0.0,min(a[1],b[1])-max(a[0],b[0]))
def distance(a,b): return max(0.0,max(a[0],b[0])-min(a[1],b[1]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("glb")
    p.add_argument("--floor",choices=("EG","OG"),default="EG")
    p.add_argument("--max-gap",type=float,default=0.60)
    args=p.parse_args()
    doc,blob=read_glb(args.glb)
    walls=[];doors=[]
    for n in doc["nodes"]:
        name=n.get("name","")
        if "mesh" not in n:continue
        if name.startswith("Innen__Innenwand_DXF_"+args.floor+"_"):
            if any(k in n for k in ("matrix","translation","rotation","scale")):
                raise ValueError("Nonidentity wall node: "+name)
            lo,hi=bounds(doc,blob,n["mesh"])
            x=(lo[0],hi[0]);z=(lo[2],hi[2])
            axis="X" if x[1]-x[0]>z[1]-z[0] else "Z"
            walls.append(dict(name=name,x=x,z=z,y=(lo[1],hi[1]),axis=axis))
        elif name.startswith("Innen__"+args.floor+"_Tuer_") and name.endswith("_Sturz"):
            lo,hi=bounds(doc,blob,n["mesh"])
            doors.append(dict(name=name,x=(lo[0],hi[0]),z=(lo[2],hi[2])))
    if not walls:raise ValueError("No walls found")
    print(f"{args.floor}: {len(walls)} wall segments, {len(doors)} door lintels")
    print("Interior wall heights (model):",sorted({tuple(round(v,3) for v in w["y"]) for w in walls}))
    print("Confirmed finished clear room height: 2.50 m (not automatically wall mesh height)")
    candidates=[]
    for i,a in enumerate(walls):
        for b in walls[i+1:]:
            if a["axis"]!=b["axis"]:continue
            main="x" if a["axis"]=="X" else "z"
            side="z" if main=="x" else "x"
            if overlap(a[side],b[side])<0.025:continue
            gap=distance(a[main],b[main])
            if not 0.008<gap<=args.max_gap:continue
            g0=min(a[main][1],b[main][1]);g1=max(a[main][0],b[main][0])
            if g0>=g1:continue
            door_hit=[]
            for d in doors:
                if overlap(d[side],a[side])>0.025 and overlap(d[main],(g0,g1))>0.01:
                    door_hit.append(d["name"])
            candidates.append((gap,a,b,main,side,g0,g1,door_hit))
    print("\nCollinear wall interruptions (including covered junctions):")
    if not candidates:print("  No short collinear gaps detected; inspect perpendicular joints.")
    for gap,a,b,main,side,g0,g1,door_hit in sorted(candidates,key=lambda c:c[0]):
        print(f"  {gap:.3f}m {main}={g0:.3f}..{g1:.3f}; {a['name']} / {b['name']}")
        covering=[w["name"] for w in walls if w is not a and w is not b and
                  overlap(w[main],(g0,g1))>=gap-0.008 and
                  overlap(w[side],a[side])>=min(0.025,a[side][1]-a[side][0])-0.005]
        if door_hit:print("    DOOR: "+", ".join(door_hit)+" (do not fill)")
        elif covering:print("    COVERED by "+", ".join(covering)+" (do not fill)")
        else:print("    UNCOVERED candidate; verify against plan before filling")
    print("\nPerpendicular near-miss T-joints (within 0.30m):")
    seen=set();count=0
    for a in walls:
        for b in walls:
            if a["axis"]==b["axis"]:continue
            # Endpoint of a should meet the band of b; do not report real intersections.
            main="x" if a["axis"]=="X" else "z"
            side="z" if main=="x" else "x"
            for end in a[main]:
                near=distance((end,end),b[main])
                side_gap=distance(a[side],b[side])
                if near<=0.03 and 0.008<side_gap<=0.30:
                    key=(a["name"],b["name"],round(side_gap,3))
                    if key in seen:continue
                    seen.add(key);count+=1
                    cover=[w["name"] for w in walls if w is not a and w is not b and
                           overlap(w[main],(end,end+0.001))>0 and
                           overlap(w[side],a[side])>0.02]
                    label="potentially covered by "+", ".join(cover) if cover else "check T-junction"
                    print(f"  {side_gap:.3f}m: {a['name']} -> {b['name']} ({label})")
    if not count:print("  None within threshold.")
    print("\nNo model was changed. Door gaps and deliberate openings require plan verification.")
if __name__=="__main__":main()
