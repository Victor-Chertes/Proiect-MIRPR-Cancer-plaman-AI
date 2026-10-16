# Detecția cancerului pulmonar din imagini CT

Proiect MIRPR 2026–2027. „Biopsie virtuală”: aplicație web în care medicul încarcă o
scanare CT a toracelui (volum NIfTI, DICOM sau o felie 2D) împreună cu vârsta și sexul
pacientului, iar un model AI estimează probabilitatea ca tumora să exprime fiecare
biomarker (EGFR, ALK, KRAS, PD-L1). Problema este de clasificare multi-label.

> **Etapa 1 (flow-ul de bază):** fluxul încărcare → analiză → rezultat funcționează cap
> la cap. Predicția este hard-codată în `software-solution/backend/model.py`
> (`predict(volum, vârstă, sex)`) și va fi înlocuită cu modelul antrenat în etapele
> următoare, fără alte modificări în API sau interfață.

## Funcționalități

- încărcare scanare CT (NIfTI `.nii` / `.nii.gz`, DICOM `.dcm`, PNG/JPEG/…) sau caz demo
  (volum CT sintetic cu nodul și mască de segmentare, generat în browser);
- date clinice: cod pacient (opțional), vârstă, sex;
- vizualizare volum: planuri axial / coronal / sagital, navigare prin felii (slider sau
  rotița mouse-ului), ferestre pulmonar / mediastin, suprapunerea măștii de segmentare
  (încărcată ca NIfTI separat);
- rezultate per biomarker: probabilitate, prag de decizie, pozitiv/negativ;
- export raport JSON și PDF (din dialogul de printare);
- istoric al analizelor din sesiunea curentă.

## Echipa

- RazvanDard
- Victor-Chertes
- Ciocan-Ionut

## Arhitectură

```
┌──────────────┐  POST /api/predict   ┌──────────────┐        ┌──────────────────┐
│ React (Vite) │ ───────────────────▶ │ Flask API    │ ─────▶ │ model.predict()  │
│ CT + vârstă, sex│ ◀─────────────────── │ validation   │ ◀───── │ (mock deocamdată)   │
└──────────────┘  {biomarkers[]}    └──────────────┘        └──────────────────┘
```

## Structura proiectului

```
software-solution/
  backend/    API Flask (app.py) și modelul provizoriu (model.py)
  frontend/   aplicația React (Vite)
documentation/  raport și slide-uri (etapele următoare)
```

## Rulare locală

Backend (Python 3.10+):

```bash
cd software-solution/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # http://127.0.0.1:5000
```

Frontend (Node 20+), într-un al doilea terminal:

```bash
cd software-solution/frontend
npm install
npm run dev                      # http://localhost:5173, /api e redirecționat către Flask
```

Alternativ, rulați `npm run build` în folderul frontend și deschideți
http://127.0.0.1:5000 (Flask servește și interfața).

## API

| Metodă | Rută           | Corp cerere                  | Răspuns |
| :----- | :------------- | :--------------------------- | :------- |
| GET    | `/api/health`  |                              | `{ status, model }` |
| POST   | `/api/predict` | `multipart/form-data`: `scan` (NIfTI/DICOM/imagine, ≤ 200 MB), `age` (0–120), `sex` (`M`/`F`) | `{ biomarkers, patient, model, filename, timestamp }` |

`biomarkers` este o listă de `{ name, description, probability, threshold, positive }`.
