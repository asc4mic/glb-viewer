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

## Innenausbau – Wandanschlüsse (31.10.2026)

- Die V3-Innengeometrie enthält 159 Innenobjekte einschließlich der Türlaibungen, Bodenflächen, Treppen und der beiden Kaminobjekte.
- Ein automatischer Vergleich der achsparallelen Wand-Bounding-Boxes zeigt bei EG und OG keine verbleibenden 2–85 mm Lücken zwischen nahen Wandsegmenten. Das ersetzt keine visuelle Planprüfung und erkennt keine größeren Unterbrechungen.
- Im KG besteht zwischen `Innen__Innenwand_DXF_KG_017` und `Innen__Innenwand_DXF_KG_002` eine 19-mm-Fuge an einer gemeinsamen Rückwandzone. Der V6-Builder ergänzt dort **ausschließlich** `Innen__Innenwand_DXF_KG_Anschluss_003`, x=6,41–6,45 m, Höhe −2,69 bis −0,24 m, y-Grundriss=7,22–7,41 m. Original-V3 und Original-Außenmodell bleiben unverändert.
- Kamin im EG ist als `EG_Kamin_Geschlossene_Verblendung`, im OG als `OG_Kamin_Geschlossener_Schacht_Vorentwurf` vorhanden; genaue Position und Schachtquerschnitt sind noch anhand des Plans und der Baustellenausführung abzugleichen.
- Die beiden OG-Giebelfenster bleiben zur Vermeidung widersprüchlicher Wandöffnungen zunächst im Original-Außenstand. Die Nutzerkorrektur „beide bis Fußboden“ ist weiterhin offen.

**Nächste Sichtprüfung:** Innenansicht KG/EG/OG im Viewer; EG-Büro/Wohnen bleibt offen, kein durchgehender Wandzug. Danach Kamin und bodentiefe Fenster planbasiert korrigieren.

## OG – Wandlücken oberhalb der Türen

Die V3-Geometrie besitzt sechs OG-Türstürze (U136, U138, U139, U140, U141 und U496), deren Oberkante bei 5,17 m liegt, während die angrenzenden OG-Innenwände bis 5,52 m reichen. Das erzeugt eine 35-cm-Lücke **oberhalb** jeder Tür. Der V6-Builder ergänzt sechs gesondert benannte Wandstücke auf der Grundfläche des jeweiligen Türsturzes bis zur Wandoberkante. Die Türlichte unterhalb des Sturzes bleibt unverändert. Der Export stoppt bei unerwarteter Türzahl oder Wandhöhe, statt fragwürdige Geometrie zu erzeugen. Andere mögliche OG-Wandlücken sind noch anhand einer Innenansicht zu lokalisieren.

## OG-Stiege: zentrale Brüstung (31.10.2026)

Die Nutzeransicht zeigt eine fälschlich raumhohe Trennwand zwischen den beiden Treppenläufen. Der V3-Geometrieauszug bestätigt die Segmente `Innen__Innenwand_DXF_OG_041` (x=4,855–4,985 m) und `Innen__Innenwand_DXF_OG_026` (x=4,985–5,115 m), beide z=−6,440 bis −5,380 m und y=3,000–5,520 m. Die V6-Erzeugung **überspringt nur diese beiden V3-Wände** und setzt eine massive Brüstung `Innen__OG_Stiege_Bruestung_zwischen_Laeufen` über deren kombinierte Grundfläche, y=3,00–4,00 m (vorläufig 1,00 m Höhe). Die restlichen OG-Wände und die EG–OG-Treppenläufe bleiben unverändert. Eine zweite im Screenshot markierte schmale Wandstelle wird nicht ohne eindeutige Zuordnung verändert. Geometrieprüfung im Viewer ausstehend.

### Nachtrag: geneigte Brüstungsoberkante

Die Brüstung zwischen den Treppenläufen hat keine waagrechte Oberkante: Am oberen Ende des Treppenlaufs (z=−5,38 m) liegt die Oberkante bei y=4,00 m, am unteren Ende (z=−6,44 m) bei y=3,00 m. Dazwischen verläuft sie geradlinig geneigt. Das ist eine schematische Visualisierung der Schräge; die endgültige Brüstungshöhe über den einzelnen Stufen ist vor Ausführung zu prüfen. Die Stufen bleiben unverändert.

## EG – Türsturz-Lücken (31.10.2026)

Die aus V3 ausgelesenen fünf EG-Türstürze `U186`, `U119`, `U111`, `U110`, `U107` enden bei y=2,20 m. Alle 26 regulären EG-Innenwandsegmente reichen bis y=2,70 m. Der V6-Builder ergänzt daher über den fünf Türstürzen jeweils ein 0,50 m hohes Wandstück mit identischer Grundfläche zum Türsturz. Die lichte Türhöhe und Türpfosten bleiben unverändert. Andere markierte Anschlüsse müssen weiterhin auf ihre tatsächliche Ursache überprüft werden; das Modell wird nicht pauschal geschlossen.

## Verbindliche Innenraumhöhen und EG-Wandanschlüsse

Nutzerbestätigung: Die **lichte Raumhöhe im EG und OG beträgt jeweils 2,50 m**. Die im V3-Modell vorhandenen Rohbau-Wandoberkanten EG y=2,70 m und OG y=5,52 m dürfen nicht ohne Kenntnis von Rohdecke, Fußbodenaufbau und abgehängten Decken auf 2,50 m gekürzt werden. Tür- und Wandöffnungen müssen an den entsprechenden tatsächlichen Deckenaufbau anschließen.

Im EG zeigen Nutzerbilder eine vom Boden bis zur Decke fehlende Wandfläche an einem T-förmigen Anschluss; **kein Vorsprung** soll hinzugefügt werden. Die Lage ist bildlich, aber noch nicht eindeutig einer V3-Wand-ID zugeordnet. Das Skript `scripts/audit_interior_wall_gaps.py` prüft zunächst kurze kollineare Unterbrechungen, modellierte Türen und verdächtige T-Anschlüsse. Es ändert keine Geometrie. Keine blinde Auffüllung von Durchgängen oder Treppenöffnungen.

Aufruf: `python3 scripts/audit_interior_wall_gaps.py public/models/Schaffernak_Haus_V3.glb --floor EG`.

## EG – Ergebnis der Wandanschlussprüfung

Die V3-Prüfung meldete vier 13-cm-Unterbrechungen und zwei T-Anschluss-Kandidaten. Einige der scheinbaren Lücken sind bereits von querlaufenden Wänden oder den V3-Anschlussstücken `EG_Anschluss_001/002` besetzt; diese dürfen nicht doppelt aufgefüllt werden. Ein konkreter, geometrisch unbelegter Anschluss liegt zwischen `Innen__Innenwand_DXF_EG_011` (Ende x=8,67), `...EG_012` (Beginn x=8,80) und `...EG_038` (Ende z=−5,25). V6 ergänzt **nur dort** `Innen__Innenwand_DXF_EG_Anschluss_003` über x=8,67–8,80 m, z=−5,25 bis −5,12 m und Rohwandhöhe y=0,03–2,70 m. Die bestätigte lichte Raumhöhe beträgt weiterhin 2,50 m; der Rohbau-/Deckenaufbau wird nicht eigenmächtig verändert. Andere im Screenshot sichtbare Fugen bleiben zur Sichtprüfung offen.
