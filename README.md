# Detecția cancerului pulmonar din imagini CT

Proiect MIRPR 2026–2027. Aplicație web în care utilizatorul încarcă o imagine CT a
toracelui, iar un model AI o clasifică drept **POZITIV** (semne de nodul malign) sau
**NEGATIV**.

> **Etapa 1 (flow-ul de bază):** fluxul încărcare → analiză → rezultat funcționează cap
> la cap. Predicția este hard-codată în `software-solution/backend/model.py` și va fi
> înlocuită cu modelul antrenat în etapele următoare.

## Echipa

- RazvanDard
- _(de completat)_

## Arhitectură

```
┌──────────────┐  POST /api/predict   ┌──────────────┐        ┌──────────────────┐
│ React (Vite) │ ───────────────────▶ │ Flask API    │ ─────▶ │ model.predict()  │
│ încărcare + UI  │ ◀─────────────────── │ validation   │ ◀───── │ (mock deocamdată)   │
└──────────────┘  {prediction, conf}  └──────────────┘        └──────────────────┘
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
| POST   | `/api/predict` | `multipart/form-data`, câmpul `image` (PNG/JPEG/BMP/TIFF/WebP, ≤ 20 MB) | `{ prediction, model, filename, timestamp }` |

`prediction` este `"POSITIVE"` sau `"NEGATIVE"`.
