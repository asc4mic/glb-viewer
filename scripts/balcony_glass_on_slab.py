"""Deterministic balcony glass railing design directly on the concrete slab.

Replaces only the old Gelaender_vorn/links/rechts glass assembly, including
cantilevered steel arms and brackets. Coordinates use master XYZ, metres.
This is a visualization, not structural or glazing engineering.
"""
import re

PREFIX=re.compile(r"^Gelaender_(vorn|links|rechts)_")

def box(name, group, color, x0,x1,y0,y1,z0,z1):
    if not (x0<x1 and y0<y1 and z0<z1):
        raise ValueError("Invalid railing box: "+name)
    v=[[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
       [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]]
    f=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],
       [0,1,5],[0,5,4],[1,2,6],[1,6,5],
       [2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    return {"name":name,"group":group,"c":color,"v":v,"f":f}

def replace_glass_railing(items):
    original=[o for o in items if PREFIX.match(o["name"])]
    if len(original)<30:
        raise ValueError("Expected original balcony glass railing is missing")
    updated=[o for o in items if not PREFIX.match(o["name"])]
    # Two front spans terminate at the existing front posts.
    # Left and right returns stop at the nearby timber post groups.
    spans=[
        ("vorn_1","x",-2.80,2.54,-2.90),
        ("vorn_2","x",2.74,7.92,-2.90),
        ("links","y",-2.80,-1.25,-2.90),
        ("rechts","y",-2.80,-0.97,8.02),
    ]
    silver="#B9C1C7";glass="#DCEEF4";film="#C7E4EE"
    for label,axis,a,b,fixed in spans:
        # 60 mm U channel, 100 mm high, seated on slab top Z=-0.05.
        # Glass sits in the channel and extends to Z=0.95.
        if axis=="x":
            updated.append(box("Gelaender_Neu_"+label+"_Schiene_Boden","Edelstahl",silver,
                               a,b,fixed-.03,fixed+.03,-.05,-.04))
            for side,lo,hi in [("Aussen",fixed-.03,fixed-.02),
                               ("Innen",fixed+.02,fixed+.03)]:
                updated.append(box("Gelaender_Neu_"+label+"_Schiene_"+side,"Edelstahl",silver,
                                   a,b,lo,hi,-.04,.05))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Aussen","Glas",glass,
                               a+.01,b-.01,fixed-.01,fixed-.001,.02,.95))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Folie","Glasfolie",film,
                               a+.01,b-.01,fixed-.001,fixed+.001,.02,.95))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Innen","Glas",glass,
                               a+.01,b-.01,fixed+.001,fixed+.01,.02,.95))
        else:
            updated.append(box("Gelaender_Neu_"+label+"_Schiene_Boden","Edelstahl",silver,
                               fixed-.03,fixed+.03,a,b,-.05,-.04))
            for side,lo,hi in [("Aussen",fixed-.03,fixed-.02),
                               ("Innen",fixed+.02,fixed+.03)]:
                updated.append(box("Gelaender_Neu_"+label+"_Schiene_"+side,"Edelstahl",silver,
                                   lo,hi,a,b,-.04,.05))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Aussen","Glas",glass,
                               fixed-.01,fixed-.001,a+.01,b-.01,.02,.95))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Folie","Glasfolie",film,
                               fixed-.001,fixed+.001,a+.01,b-.01,.02,.95))
            updated.append(box("Gelaender_Neu_"+label+"_VSG_Innen","Glas",glass,
                               fixed+.001,fixed+.01,a+.01,b-.01,.02,.95))
    return updated, {"removed_old_railing_meshes":len(original),
                     "added_slab_mounted_railing_meshes":len(updated)-(len(items)-len(original)),
                     "mounting":"U channels directly on balcony slab, between existing posts",
                     "status":"visualization; exact glass dimensions and anchorage to be verified"}
