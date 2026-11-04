"""Plan-guided KG->EG concrete winder stairs for the Schaffernak V6 GLB.

DXF: STIEGE__$-259, 15 rises at 18.13 cm over 2.72 m.
Descending from EG: left flight, clockwise/right-hand wind, right flight.
Footprints rounded to centimetres from the construction plan.
Concrete slab thickness and oak finish are visualization assumptions.
"""
import struct

RISERS = 15
LEVEL_DIFFERENCE_M = 2.72
CONCRETE_DEPTH_M = 0.22
OAK_FINISH_M = 0.018


def kg_tread_footprints():
    # Plan x/depth in metres; glTF uses (x, elevation, -depth).
    left = [
        ((3.80, 5.37), (4.86, 5.37)),
        ((3.80, 5.66), (4.86, 5.66)),
        ((3.80, 5.91), (4.86, 5.91)),
        ((3.80, 6.24), (4.86, 6.06)),
        ((3.80, 6.60), (4.86, 6.19)),
    ]
    outer = [
        (3.80, 6.60), (3.80, 7.09), (4.11, 7.41),
        (4.61, 7.41), (5.48, 7.41), (6.17, 7.21), (6.17, 6.89),
    ]
    inner = [
        (4.86, 6.19), (4.86, 6.30), (4.86, 6.37),
        (4.91, 6.44), (5.07, 6.44), (5.12, 6.38), (5.12, 6.30),
    ]
    right = [
        ((6.17, 6.89), (5.12, 6.30)),
        ((6.17, 6.52), (5.12, 6.22)),
        ((6.17, 6.22), (5.12, 6.02)),
        ((6.17, 5.92), (5.12, 5.82)),
        ((6.17, 5.62), (5.12, 5.62)),
        ((6.17, 5.37), (5.12, 5.37)),
    ]
    polys = []
    for i in range(4):
        polys.append([left[i][0], left[i+1][0], left[i+1][1], left[i][1]])
    for i in range(6):
        polys.append([outer[i], outer[i+1], inner[i+1], inner[i]])
    for i in range(5):
        polys.append([right[i][0], right[i+1][0], right[i+1][1], right[i][1]])
    assert len(polys) == RISERS
    return polys


def add_kg_concrete_winder(doc, accessor, existing_names):
    """Append 15 concrete treads and parquet tops to a glTF document."""
    concrete = len(doc["materials"])
    doc["materials"].append({
        "name": "Kellerstiege_Beton", "doubleSided": True,
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.66, 0.65, 0.63, 1.0],
            "metallicFactor": 0, "roughnessFactor": 0.95,
        },
    })
    oak = len(doc["materials"])
    doc["materials"].append({
        "name": "Kellerstiege_Eichenparkett", "doubleSided": True,
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.65, 0.45, 0.27, 1.0],
            "metallicFactor": 0, "roughnessFactor": 0.72,
        },
    })
    created = []
    for step, polygon in enumerate(kg_tread_footprints(), 1):
        top = -step * LEVEL_DIFFERENCE_M / RISERS
        for suffix, low, high, material in [
            ("Beton", top-CONCRETE_DEPTH_M, top-OAK_FINISH_M, concrete),
            ("Eichenparkett", top-OAK_FINISH_M, top, oak),
        ]:
            name = f"Innen__Treppe_KG_EG_{suffix}_Stufe_{step:02d}"
            if name in existing_names:
                raise ValueError("KG stair name collision: " + name)
            vertices = [(x, low, -depth) for x, depth in polygon]
            vertices += [(x, high, -depth) for x, depth in polygon]
            n = len(polygon)
            faces = []
            for k in range(1, n-1):
                faces.extend((0, k+1, k))
                faces.extend((n, n+k, n+k+1))
            for k in range(n):
                j = (k+1) % n
                faces.extend((k, j, n+j, k, n+j, n+k))
            flat = [v for vertex in vertices for v in vertex]
            mins = [min(p[k] for p in vertices) for k in range(3)]
            maxs = [max(p[k] for p in vertices) for k in range(3)]
            pos = accessor(struct.pack("<"+"f"*len(flat), *flat),
                           5126, "VEC3", len(vertices), (mins, maxs))
            indices = accessor(struct.pack("<"+"I"*len(faces), *faces),
                               5125, "SCALAR", len(faces), target=34963)
            mesh_id = len(doc["meshes"])
            doc["meshes"].append({"name": name, "primitives": [{
                "attributes": {"POSITION": pos},
                "indices": indices, "material": material, "mode": 4,
            }]})
            node_id = len(doc["nodes"])
            doc["nodes"].append({"name": name, "mesh": mesh_id})
            doc["scenes"][0]["nodes"].append(node_id)
            created.append(name)
    return {
        "source": "KG floor plan and DXF STIEGE__$-259",
        "direction_down": "left at EG, turn right, finish right at KG",
        "construction": "concrete with oak parquet finish",
        "riser_count": RISERS,
        "riser_height_m": LEVEL_DIFFERENCE_M / RISERS,
        "concrete_depth_m_assumed": CONCRETE_DEPTH_M,
        "parquet_thickness_m_assumed": OAK_FINISH_M,
        "created_meshes": len(created),
        "tread_boundaries": "DXF plan-derived, rounded to cm; on-site verification pending",
    }
