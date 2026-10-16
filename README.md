# PulmoScan: lung cancer detection from CT scans

MIRPR 2026–2027 project. A web app where a user uploads a chest CT slice and an AI
model classifies it as **POSITIVE** (signs of a malignant nodule) or **NEGATIVE**.

> **Stage 1 (basic flow):** the full upload → analyze → result flow works end to end.
> The prediction is hard-coded in `software-solution/backend/model.py` and will be
> replaced by the trained model in a later stage.

## Team

- RazvanDard
- _(add teammates)_

## How it works

```
┌──────────────┐  POST /api/predict   ┌──────────────┐        ┌──────────────────┐
│ React (Vite) │ ───────────────────▶ │ Flask API    │ ─────▶ │ model.predict()  │
│ upload + UI  │ ◀─────────────────── │ validation   │ ◀───── │ (mock for now)   │
└──────────────┘  {prediction, conf}  └──────────────┘        └──────────────────┘
```

## Project layout

```
software-solution/
  backend/    Flask API (app.py) and the model placeholder (model.py)
  frontend/   React app (Vite)
documentation/  report and slides (later stages)
```

## Running locally

Backend (Python 3.10+):

```bash
cd software-solution/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # http://127.0.0.1:5000
```

Frontend (Node 20+), in a second terminal:

```bash
cd software-solution/frontend
npm install
npm run dev                      # http://localhost:5173, /api is proxied to Flask
```

To serve everything from Flask instead, run `npm run build` in the frontend folder and
open http://127.0.0.1:5000.

## API

| Method | Path           | Body                         | Response |
| :----- | :------------- | :--------------------------- | :------- |
| GET    | `/api/health`  |                              | `{ status, model }` |
| POST   | `/api/predict` | `multipart/form-data`, field `image` (PNG/JPEG/BMP/TIFF/WebP, ≤ 20 MB) | `{ prediction, confidence, model, inference_ms, filename, timestamp }` |

`prediction` is `"POSITIVE"` or `"NEGATIVE"`.
