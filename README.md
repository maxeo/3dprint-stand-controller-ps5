# Stand Controller PS5

Stand da scrivania ricavato dal "Dual PS5 Controller stand": un controller sul braccio alto, cuffie sul gancio, portapenne avvitato alla base al posto del controller basso e culla per la custodia delle HUAWEI FreeBuds 3 dietro la colonna. Apri **guida.html** per la vista 3D, il montaggio e la lista di stampa.

## Contenuto

- `guida.html`: istruzioni, parametri di stampa e vista 3D interattiva
- `stl/`: i 3 pezzi da stampare, una copia ciascuno, orientati per la stampa
  - `P01_Base`: base originale + perno filettato Ø20 × 7 (passo 2,5) + culla FreeBuds 3
  - `P02_Sostegno`: holder originale senza il braccio basso
  - `P03_Portapenne`: Ø48 × 90, madrevite sul fondo (gioco radiale 0,35 mm)
- `blender/Stand_Controller_PS5.blend`: assieme (collezione `PEZZI_MONTATI`), originali (`ORIGINALE`, nascosta) e custodia di riferimento (`RIFERIMENTI`)
- `blender/costruisci.py`: genera .blend, STL e `dati/geometria.json` dagli originali (anche come testo nel .blend)
- `dati/`: `guida_spec.json` (sorgente della guida) e `geometria.json` (ingombri, volumi, giochi, mesh chiuse)
- `originale/`: i due 3mf scaricati, le loro mesh in STL e l'anteprima

Rigenerare i pezzi e la guida:

```
blender -b --factory-startup --python blender/costruisci.py
python ~/.claude/skills/guida-stampa-3d/scripts/build_guide.py dati/guida_spec.json
```

## Note

- Custodia FreeBuds 3: Ø60,9 × 21,8 mm dalla scheda Huawei; tasca Ø62 × 23 mm. Da verificare sulla custodia reale.
- Nessun pezzo nuovo è ancora stato stampato: filetto e culla sono da provare.
- La colonna sdraiata misura 248,8 mm: sul piatto da 250 va messa in diagonale.
