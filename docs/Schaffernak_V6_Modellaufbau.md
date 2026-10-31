# Schaffernak V6 – sauberer Modellaufbau

## Verbindliche Quellen
- **Außenanlage:** `asc4mic/haus-schaffernak-3d/model/model_items.json` (Originalmodell mit allen 687 benannten Bauteilen: Carport, Stiege, Überdachungen, Geländer, Gelände usw.).
- **Innenräume:** `public/models/Schaffernak_Haus_V3.glb`, **nur** Objekte mit Präfix `Innen__` und `EG_Kamin_`/`OG_Kamin_`.
- **Nicht verwenden:** V4 und V5 als Geometriequellen. Keine heuristische Ergänzung fehlender Außenbauteile.

## Auf dem Arduino Uno Q

```bash
cd /media/arduino/SD-EXT4/glb-viewer
git pull --ff-only

python3 scripts/build_schaffernak_clean.py \
  --exterior /tmp/schaffernak-viewer-source/model/model_items.json \
  --interior public/models/Schaffernak_Haus_V3.glb \
  --output public/models/Schaffernak_Haus_V6.glb

cat public/models/Schaffernak_Haus_V6.glb.report.json
npm run build
sudo systemctl restart glb-viewer
```

Der Builder stoppt bei fehlenden Innenraumobjekten, unvollständigem Außenmodell, doppelten Namen oder problematischen Transformationen, statt ein stillschweigend falsches Modell zu exportieren. Erst nach erfolgreichem Export bauen und neu starten.

## Glasgeländer – neue Montagevariante

Beim sauberen V6-Export ersetzt `scripts/balcony_glass_on_slab.py` **nur** die bisherige Balkon-Glasgeländerkonstruktion (`Gelaender_vorn_*`, `Gelaender_links_*`, `Gelaender_rechts_*`). Die alten auskragenden Vierkantträger, Fußlaschen, Schrauben, Glasflächen und Schienen werden nicht übernommen. Stattdessen entstehen neue VSG-Glasflächen in U-förmigen Edelstahl-Bodenschienen direkt auf der Balkon-Betonplatte, zwischen den vorhandenen Stützen. Alle anderen Originalbauteile bleiben unverändert. Das ursprüngliche `model_items.json` wird nicht überschrieben.

**Achtung:** Die dargestellten Glas-/Schienenabmessungen und Anschlüsse sind schematisch und kein statischer Nachweis. Sichtprüfung der Endpunkte erforderlich.

## Bewusst noch offen

- **Fensterkorrekturen:** V6 verwendet zunächst die Fenster und Wandöffnungen des vollständigen Original-Außenmodells. Die neueren Korrekturen an den beiden bodentiefen OG-Giebelfenstern werden **nicht ungeprüft** aus V3 übernommen, weil dabei auch die korrespondierenden Außenwandöffnungen konsistent ersetzt werden müssen.
- **Kamin:** Nur ausdrücklich als `EG_Kamin_`/`OG_Kamin_` benannte V3-Bauteile werden übernommen. Die Lage im OG muss weiterhin gegen die Pläne geprüft werden.
- **Kontrolle:** Nach dem Export besonders Dachanschlüsse, Carport, Stützen, Geländer, Stiege, Balkonplatte und die OG-Fenster visuell prüfen.

Die bisherigen V3/V4/V5-Dateien werden nicht überschrieben. Die neue Datei heißt `Schaffernak_Haus_V6.glb`, mit maschinenlesbarem `.report.json`.
