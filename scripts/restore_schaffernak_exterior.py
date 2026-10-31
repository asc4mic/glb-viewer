#!/usr/bin/env python3
"""Restore complete original exterior, including terrain, roof details, columns and railings.

Pure Python stdlib: merges the original selected meshes into the V3 GLB without
changing the corrected interior walls and windows. Writes V5 GLB.
"""
import argparse
import json
import struct
from pathlib import Path

# Restore the finished exterior from the original master model, not just terrain.
# House shell and window groups are intentionally excluded: V3 has corrected windows
# and additional interiors which must remain authoritative.
RESTORE_GROUPS = {
    "Beton", "Entwurf", "Ueberdachung", "Edelstahl", "Glas",
    "Glasfolie", "Gelaende", "Strasse", "Carport", "Holz",
    "Metall", "Mauer",
}

OLD_TERRAIN = {
    "Gelaende_links_schematisch",
    "Gelaende_hinten_schematisch",
    "Gelaende_linke_Stuetzen_verdeckt",
    "Carport_Unterbau_Fuellung",
    "Strasse_Unterbau_schematisch",
}

def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from("<III", data)
    if (magic, version, total) != (0x46546C67, 2, len(data)):
        raise ValueError("Not a valid glTF 2.0 GLB")
    at = 12
    chunks = {}
    while at < len(data):
        size, kind = struct.unpack_from("<II", data, at)
        at += 8
        chunks[kind] = data[at:at+size]
        at += size
    return json.loads(chunks[0x4E4F534A]), bytearray(chunks[0x004E4942])

def write_glb(path, gltf, binary):
    while len(binary) % 4:
        binary.append(0)
    gltf["buffers"][0]["byteLength"] = len(binary)
    payload = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(payload) + 8 + len(binary))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(header + struct.pack("<II", len(payload), 0x4E4F534A)
                           + payload + struct.pack("<II", len(binary), 0x004E4942) + binary)

def restore(source, terrain_json, target):
    gltf, binary = read_glb(source)
    items = json.loads(Path(terrain_json).read_text(encoding="utf-8"))
    original_names = {n.get("name") for n in gltf["nodes"] if n.get("name") not in OLD_TERRAIN}
    terrain = [o for o in items if o.get("group") in RESTORE_GROUPS
               and o.get("name") not in original_names]
    if not terrain:
        raise ValueError("No missing exterior meshes found in source model")
    if len(gltf.get("buffers", [])) != 1:
        raise ValueError("Expected exactly one GLB binary buffer")
    roots = gltf["scenes"][gltf.get("scene", 0)]["nodes"]
    root = gltf["nodes"][roots[0]]
    if "children" not in root:
        raise ValueError("Expected the original world node with children")
    root["children"] = [
        idx for idx in root["children"]
        if gltf["nodes"][idx].get("name") not in OLD_TERRAIN
    ]
    mats = gltf.setdefault("materials", [])

    def add_accessor(blob, component, kind, count, bounds=None, target_hint=34962):
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(blob)
        view = len(gltf["bufferViews"])
        gltf["bufferViews"].append({
            "buffer": 0, "byteOffset": offset, "byteLength": len(blob),
            "target": target_hint
        })
        acc = len(gltf["accessors"])
        data = {"bufferView": view, "componentType": component, "count": count, "type": kind}
        if bounds:
            data["min"], data["max"] = bounds
        gltf["accessors"].append(data)
        return acc

    for o in terrain:
        vertices = [(float(x), float(z), -float(y)) for x, y, z in o["v"]]
        faces = [int(i) for face in o["f"] for i in face]
        if not vertices or not faces:
            raise ValueError("Empty terrain mesh: " + o["name"])
        flat = [v for point in vertices for v in point]
        position = add_accessor(
            struct.pack("<" + "f" * len(flat), *flat), 5126, "VEC3", len(vertices),
            ([min(v[i] for v in vertices) for i in range(3)],
             [max(v[i] for v in vertices) for i in range(3)])
        )
        indices = add_accessor(
            struct.pack("<" + "I" * len(faces), *faces), 5125, "SCALAR", len(faces),
            target_hint=34963
        )
        color = o["c"]
        rgb = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        material = len(mats)
        mats.append({"name": o["name"], "doubleSided": True,
                     "pbrMetallicRoughness": {
                         "baseColorFactor": rgb + [1.0],
                         "metallicFactor": 0.0, "roughnessFactor": 0.95}})
        mesh_id = len(gltf["meshes"])
        gltf["meshes"].append({
            "name": o["name"],
            "primitives": [{"attributes": {"POSITION": position},
                            "indices": indices, "material": material, "mode": 4}]
        })
        node_id = len(gltf["nodes"])
        gltf["nodes"].append({"name": o["name"], "mesh": mesh_id})
        root["children"].append(node_id)
    write_glb(target, gltf, binary)
    print("Restored", len(terrain), "missing original exterior meshes; saved", target)
    print("Original V3 retained:", source)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--terrain", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    restore(args.input, args.terrain, args.output)
