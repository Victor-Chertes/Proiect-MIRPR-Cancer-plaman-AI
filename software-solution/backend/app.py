"""Flask API serving lung cancer predictions to the React frontend."""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

import model

# 2D slices, NIfTI volumes (.nii / .nii.gz) and DICOM files.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp", "nii", "gz", "dcm"}
SEXES = {"M", "F"}
MAX_UPLOAD_MB = 200
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def allowed(filename: str) -> bool:
    name = filename.lower()
    if name.endswith(".gz"):
        return name.endswith(".nii.gz")
    return "." in name and name.rsplit(".", 1)[1] in ALLOWED_EXTENSIONS


def parse_age(value):
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None
    return age if 0 <= age <= 120 else None


@app.get("/api/health")
def health():
    return jsonify(status="ok", model=model.MODEL_NAME)


@app.post("/api/predict")
def predict():
    file = request.files.get("scan")
    if file is None or file.filename == "":
        return jsonify(error="Nu a fost încărcată nicio scanare."), 400
    if not allowed(file.filename):
        return jsonify(error="Format de fișier neacceptat."), 415

    age = parse_age(request.form.get("age"))
    if age is None:
        return jsonify(error="Vârsta trebuie să fie un număr între 0 și 120."), 400
    sex = request.form.get("sex", "").upper()
    if sex not in SEXES:
        return jsonify(error="Sexul trebuie să fie M sau F."), 400

    data = file.read()
    if not data:
        return jsonify(error="Fișierul încărcat este gol."), 400

    result = model.predict(data, age, sex)
    return jsonify(
        filename=file.filename,
        patient={"age": age, "sex": sex},
        timestamp=datetime.now(timezone.utc).isoformat(),
        **result,
    )


@app.errorhandler(413)
def too_large(_):
    return jsonify(error=f"Fișierul depășește {MAX_UPLOAD_MB} MB."), 413


# Serve the production build of the frontend if it exists (npm run build).
@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def frontend(path):
    if not os.path.isdir(FRONTEND_DIST):
        return "Frontend not built. Run `npm run build` in software-solution/frontend.", 404
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
