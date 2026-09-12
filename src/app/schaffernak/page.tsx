import fs from "node:fs";
import path from "node:path";
import Link from "next/link";
import SimpleGLBViewer from "@/src/components/SimpleGLBViewer";

function getVersionedModelUrl() {
  const filePath = path.join(process.cwd(), "public/models/Schaffernak_Haus.glb");
  const stats = fs.statSync(filePath);
  const version = `${stats.size}-${Math.floor(stats.mtimeMs)}`;
  return `/models/Schaffernak_Haus.glb?v=${version}`;
}

export default function SchaffernakPage() {
  const modelUrl = getVersionedModelUrl();

  return (
    <main className="min-h-screen bg-[#030712] text-white px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-400/80">
              Direktlink
            </p>
            <h1 className="text-3xl font-bold tracking-tight">Schaffernak Haus</h1>
            <p className="mt-2 text-sm text-white/50">
              Das Modell lädt direkt ohne Upload. Link kann direkt geteilt werden.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10"
          >
            Zur Startseite
          </Link>
        </div>

        <SimpleGLBViewer url={modelUrl} />
      </div>
    </main>
  );
}
