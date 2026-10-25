# Stand Controller PS5

Stand da scrivania ricavato dal "Dual PS5 Controller stand": un controller sul braccio alto, cuffie sul gancio, portapenne avvitato alla base al posto del controller basso e culla per la custodia delle HUAWEI FreeBuds 3 dietro il montante. Apri **guida.html** per la vista 3D, il montaggio e la lista di stampa.

## Contenuto

- `guida.html`: istruzioni, parametri di stampa e vista 3D interattiva
- `stl/`: i 3 pezzi da stampare, una copia ciascuno, orientati per la stampa
  - `P01_Base` (basamento): base originale allargata da Ø180 a Ø190 + madrevite incassata Ø41,8 profonda 6 mm (passo 2,5) + culla FreeBuds 3 + due fori svasati per le viti
  - `P02_Sostegno` (montante): holder originale senza il braccio basso, con due fori guida Ø3,3 per le viti
  - `P03_Portapenne`: a botte Ø45–48 × 90, parete forata a celle di Voronoi, vite Ø41 sul fondo (gioco radiale 0,4 mm)
- Viteria: 2 viti autofilettanti a testa svasata 4 × 20 mm, da sotto la base nel piede del montante; la sede del tenone ha 0,15 mm di gioco per lato
- `blender/Stand_Controller_PS5.blend`: assieme (collezione `PEZZI_MONTATI`), originali (`ORIGINALE`, nascosta) e accessori di riferimento (`RIFERIMENTI`: DualSense, custodia FreeBuds 3, cinque penne, cuffie d'esempio)
- `blender/costruisci.py`: genera .blend, STL e `dati/geometria.json` dagli originali (anche come testo nel .blend)
- `blender/accessori.py`: forme semplificate degli accessori, solo per vedere gli ingombri; il controller è appoggiato alla quota in cui tocca il braccio
- `dati/`: `guida_spec.json` (sorgente della guida) e `geometria.json` (ingombri, volumi, giochi, mesh chiuse)
- `originale/`: i due 3mf scaricati, le loro mesh in STL, l'anteprima e `riferimento_portapenne_voronoi.stl`, il vaso a Voronoi da cui viene lo stile del portapenne (semplificato da 5,8 milioni a 29 000 triangoli)

Rigenerare i pezzi e la guida:

```
blender -b --factory-startup --python blender/costruisci.py
python ~/.claude/skills/guida-stampa-3d/scripts/build_guide.py dati/guida_spec.json
```

## Note

- Custodia FreeBuds 3: Ø60,9 × 21,8 mm dalla scheda Huawei; tasca Ø62 × 23 mm. Da verificare sulla custodia reale.
- Nessun pezzo nuovo è ancora stato stampato: filetto e culla sono da provare.
- La colonna sdraiata misura 248,8 mm: sul piatto da 250 va messa in diagonale.
