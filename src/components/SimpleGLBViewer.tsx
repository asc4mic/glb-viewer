"use client";

import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  useGLTF,
  Stage,
  Center,
  Environment,
  useProgress,
  Html,
} from "@react-three/drei";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import { SimpleGLBViewerProps } from "../types";

type SupportLabel = {
  id: string;
  name: string;
  group: string;
  color: string;
  position: [number, number, number];
};

const Model = ({ url, showLabels }: { url: string; showLabels: boolean }) => {
  const { scene } = useGLTF(url);
  const [labels, setLabels] = useState<SupportLabel[]>([]);

  useEffect(() => {
    fetch("/support-labels.json")
      .then((response) => response.json())
      .then((value: SupportLabel[]) => setLabels(value))
      .catch(() => setLabels([]));
  }, []);

  return (
    <Center>
      <primitive object={scene} />
      {showLabels && labels.map((label) => (
        <Html key={label.id} position={label.position} center distanceFactor={8} style={{ pointerEvents: "none" }}>
          <span
            title={label.name}
            style={{
              color: "#ffffff",
              background: "rgba(3, 7, 18, .78)",
              border: `1px solid ${label.color}`,
              borderRadius: 4,
              padding: "1px 3px",
              fontSize: 9,
              lineHeight: 1,
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
              whiteSpace: "nowrap",
            }}
          >
            {label.id}
          </span>
        </Html>
      ))}
    </Center>
  );
};

function LoadingOverlay() {
  const { active, progress } = useProgress();
  const [smoothProgress, setSmoothProgress] = useState(0);

  useEffect(() => {
    if (active) {
      if (progress > smoothProgress) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSmoothProgress(progress);
      }
    } else {
      const timeout = setTimeout(() => {
        setSmoothProgress(0);
      }, 500);
      return () => clearTimeout(timeout);
    }
  }, [progress, active, smoothProgress]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: active ? 1 : 0 }}
      transition={{ duration: 0.5 }}
      style={{ pointerEvents: active ? "auto" : "none" }}
      className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black/40 backdrop-blur-md rounded-[40px]"
    >
      <div className="relative w-16 h-16 mb-4">
        <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full" />
        <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[10px] font-bold text-blue-500">
            {Math.round(smoothProgress)}%
          </span>
        </div>
      </div>
      <p className="text-white/40 font-bold uppercase tracking-[0.2em] text-[10px] animate-pulse">
        Loading Model
      </p>
    </motion.div>
  );
}

const SimpleGLBViewer: React.FC<SimpleGLBViewerProps> = ({ url }) => {
  const [showLabels, setShowLabels] = useState(true);

  return (
    <div className="w-full h-[400px] md:h-[500px] bg-black/40 backdrop-blur-3xl rounded-[40px] border border-white/10 overflow-hidden relative shadow-2xl">
      <LoadingOverlay />
      <Canvas
        shadows
        camera={{ position: [16, 10, 16], fov: 45 }}
        gl={{ antialias: true, preserveDrawingBuffer: true }}
      >
        <Suspense fallback={null}>
          <Stage
            intensity={0.5}
            environment="apartment"
            adjustCamera={false}
            shadows="contact"
          >
            <Model url={url} showLabels={showLabels} />
          </Stage>
          <OrbitControls makeDefault enablePan={true} enableZoom={true} />
          <Environment preset="apartment" />
        </Suspense>
      </Canvas>

      <button
        type="button"
        onClick={() => setShowLabels((visible) => !visible)}
        className="absolute top-6 right-6 rounded-full border border-white/15 bg-black/50 px-4 py-2 text-xs font-semibold text-white/90 backdrop-blur-xl transition hover:bg-white/15"
        aria-pressed={showLabels}
      >
        Labels: {showLabels ? "anzeigen" : "ausblenden"}
      </button>

      {/* Label/Overlay */}
      <div className="absolute top-6 left-6 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full backdrop-blur-xl">
        <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
          3D Preview
        </span>
      </div>
    </div>
  );
};

export default SimpleGLBViewer;
