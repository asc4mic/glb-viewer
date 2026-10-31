import { Suspense } from "react";
import Home from "../views/index";

export default function Page() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-[#030712] text-white p-8">GLB-Viewer wird geladen …</main>}>
      <Home />
    </Suspense>
  );
}
