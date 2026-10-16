"""Flask API serving lung cancer predictions to the React frontend."""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

import model

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"}
MAX_UPLOAD_MB = 20
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/api/health")
def health():
    return jsonify(status="ok", model=model.MODEL_NAME)


@app.post("/api/predict")
def predict():
    file = request.files.get("image")
    if file is None or file.filename == "":
        return jsonify(error="No image uploaded."), 400
    if not allowed(file.filename):
        return jsonify(error="Unsupported file type."), 415

    data = file.read()
    if not data:
        return jsonify(error="Uploaded file is empty."), 400

    result = model.predict(data)
    return jsonify(
        filename=file.filename,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **result,
    )


@app.errorhandler(413)
def too_large(_):
    return jsonify(error=f"File is larger than {MAX_UPLOAD_MB} MB."), 413


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
