"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, OrbitControls, useGLTF } from "@react-three/drei";
import type { Object3D } from "three";
import SimpleGLBViewer from "./SimpleGLBViewer";

type Variant = { id: string; label: string; url: string; labelsUrl: string };
type Floor = "ALL" | "KG" | "EG" | "OG";

function floorOf(name: string): Floor | null {
  const m = name.match(/(?:^|__)(KG|EG|OG)(?:_|$)/);
  if (m) return m[1] as Floor;
  const b = name.match(/^Innen__.*(?:Bodenbelag|Innenwand).*_(KG|EG|OG)_/);
  return b ? (b[1] as Floor) : null;
}

function isRoof(name: string) {
  return /^(Satteldach_|Giebel_|OG_Kniestock_|Carport_Dach|Entwurf_Dach)/.test(name);
}
function isTerrain(name: string) {
  return /^(Gelaende_|Foto_Gelaende_|Mauer_)/.test(name);
}
function isInterior(name: string) {
  return name.startsWith("Innen__") || /^(EG|OG)_Kamin_/.test(name);
}

function InteriorModel({ url, floor, walls, roof, terrain, fireplace }: {
  url: string; floor: Floor; walls: boolean; roof: boolean; terrain: boolean; fireplace: boolean;
}) {
  const { scene } = useGLTF(url);
  // Clone the cached GLTF: layer visibility must not mutate the original scene.
  const model = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    model.traverse((part: Object3D) => {
      if (!("isMesh" in part) || !part.name) return;
      const name = part.name;
      const partFloor = floorOf(name);
      let visible = floor === "ALL" || !partFloor || partFloor === floor;
      if (!walls && (/_Wand|Innenwand|Kniestock|^Giebel_/.test(name))) visible = false;
      if (!roof && isRoof(name)) visible = false;
      if (!terrain && isTerrain(name)) visible = false;
      if (!fireplace && /^(EG|OG)_Kamin_/.test(name)) visible = false;
      // In a single-floor view hide common roof and exterior construction so rooms are visible.
      if (floor !== "ALL" && !partFloor && !isInterior(name) && !/^Treppe_/.test(name)) {
        visible = false;
      }
      part.visible = visible;
    });
  }, [model, floor, walls, roof, terrain, fireplace]);

  return <Center><primitive object={model} /></Center>;
}

export default function SchaffernakIntegratedViewer({
  variants, interiorAvailable, terrainV4Available,
}: { variants: Variant[]; interiorAvailable: boolean; terrainV4Available: boolean }) {
  const [variant, setVariant] = useState(terrainV4Available ? "V4" : interiorAvailable ? "V3" : "A");
  const [floor, setFloor] = useState<Floor>("ALL");
  const [walls, setWalls] = useState(true);
  const [roof, setRoof] = useState(true);
  const [terrain, setTerrain] = useState(true);
  const [fireplace, setFireplace] = useState(true);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label htmlFor="schaffernak-model">Modell</label>
        <select id="schaffernak-model" value={variant} onChange={e => setVariant(e.target.value)}
          className="rounded-xl border border-white/20 bg-slate-900 px-3 py-2 text-white">
          {terrainV4Available && <option value="V4">V4 · Innen/Außen mit Gelände</option>}
          {interiorAvailable && <option value="V3">V3 · Innen und Außen (alt)</option>}
          {variants.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
        </select>
      </div>

      {variant !== "V3" && variant !== "V4" ? (
        <SimpleGLBViewer key={variant} url={variants.find(v => v.id === variant)?.url ?? variants[0].url}
          variants={variants.filter(v => v.id === variant)} />
      ) : (
        <>
          <div className="flex flex-wrap gap-3 items-center text-sm">
            <label htmlFor="schaffernak-floor">Geschoss</label>
            <select id="schaffernak-floor" value={floor} onChange={e => setFloor(e.target.value as Floor)}
              className="rounded-xl border border-white/20 bg-slate-900 px-3 py-2 text-white">
              <option value="ALL">Alle Geschosse</option>
              <option value="KG">Keller</option>
              <option value="EG">Erdgeschoss</option>
              <option value="OG">Obergeschoss</option>
            </select>
            {([
              ["Wände", walls, setWalls],
              ["Dach", roof, setRoof],
              ["Gelände", terrain, setTerrain],
              ["Kamin", fireplace, setFireplace],
            ] as const).map(([label, value, setter]) =>
              <label key={label} className="flex items-center gap-1.5">
                <input type="checkbox" checked={value} onChange={e => setter(e.target.checked)} />{label}
              </label>
            )}
          </div>
          <div className="relative h-[60vh] min-h-[430px] overflow-hidden rounded-3xl border border-white/10 bg-slate-950">
            <Canvas camera={{ position: [16, 12, 17], fov: 45 }} gl={{ antialias: true }}>
              <ambientLight intensity={1.35} />
              <hemisphereLight args={["#f5f8ff", "#c7cbd1", 1.4]} />
              <directionalLight position={[12, 16, 12]} intensity={1.7} />
              <directionalLight position={[-12, 12, -12]} intensity={1.45} />
              <directionalLight position={[-12, 9, 12]} intensity={0.85} />
              <directionalLight position={[12, 9, -12]} intensity={0.85} />
              <Suspense fallback={null}>
                <InteriorModel url={variant === "V4" ? "/models/Schaffernak_Haus_V4.glb" : "/models/Schaffernak_Haus_V3.glb"}
                  floor={floor} walls={walls} roof={roof} terrain={terrain} fireplace={fireplace} />
              </Suspense>
              <OrbitControls makeDefault enablePan enableZoom minDistance={1} maxDistance={120} />
            </Canvas>
          </div>
          <p className="text-xs text-white/50">Ein Finger: drehen · Zwei Finger: verschieben · Finger auseinanderziehen: zoomen. Kamin- und Wanddetails sind noch im Planabgleich.</p>
        </>
      )}
    </section>
  );
}
