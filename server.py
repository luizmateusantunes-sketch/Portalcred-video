"""
PortalCred — Video Variator Backend
Deploy no Railway: adicione este arquivo + Dockerfile + requirements.txt
"""

import os
import uuid
import zipfile
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 8080))

VARIATION_PROFILES = [
    {"id": "mirror", "name": "Espelho Horizontal", "description": "Inverte horizontalmente. Muda hash sem alterar conteúdo.", "vf": "hflip", "af": "aecho=0.8:0.9:40:0.1"},
    {"id": "zoom_in", "name": "Zoom Suave", "description": "Leve zoom 1.04x — imperceptível ao espectador.", "vf": "scale=iw*1.04:ih*1.04,crop=iw/1.04:ih/1.04", "af": "atempo=1.0"},
    {"id": "color_warm", "name": "Cor Quente", "description": "Temperatura levemente mais quente na paleta.", "vf": "eq=saturation=1.08:brightness=0.02:contrast=1.02,colorbalance=rs=0.04:gs=-0.01:bs=-0.04", "af": "volume=1.03"},
    {"id": "color_cool", "name": "Cor Fria", "description": "Toque levemente azulado na paleta.", "vf": "eq=saturation=1.05:brightness=0.01,colorbalance=rs=-0.03:gs=0.01:bs=0.05", "af": "volume=0.97"},
    {"id": "speed_fast", "name": "Micro Velocidade +1%", "description": "1.01x — indetectável ao ouvido, muda fingerprint do áudio.", "vf": "setpts=0.99*PTS", "af": "atempo=1.01"},
    {"id": "speed_slow", "name": "Micro Velocidade -1%", "description": "0.99x — indetectável ao ouvido.", "vf": "setpts=1.01*PTS", "af": "atempo=0.99"},
    {"id": "crop_top", "name": "Crop Superior", "description": "Remove 8px do topo e reescala.", "vf": "crop=iw:ih-8:0:8,scale=iw:ih+8", "af": "aecho=0.9:0.95:20:0.05"},
    {"id": "noise", "name": "Micro Ruído Visual", "description": "Ruído de 3% nos frames — muda hash completamente.", "vf": "noise=alls=3:allf=t", "af": "volume=1.01"},
    {"id": "mirror_speed", "name": "Espelho + Velocidade", "description": "Combinação: espelho + 1% velocidade.", "vf": "hflip,setpts=0.99*PTS", "af": "atempo=1.01"},
    {"id": "saturation", "name": "Saturação Leve", "description": "Cores 12% mais vibrantes.", "vf": "eq=saturation=1.12:contrast=1.01", "af": "loudnorm"},
]


def apply_variation(input_path, output_path, profile):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", profile["vf"],
        "-af", profile["af"],
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "9999",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        return result.returncode == 0
    except Exception:
        return False


@app.route("/health", methods=["GET"])
def health():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        ffmpeg_ok = True
    except Exception:
        ffmpeg_ok = False
    return jsonify({"status": "ok", "ffmpeg": ffmpeg_ok, "variations_available": len(VARIATION_PROFILES)})


@app.route("/variations", methods=["GET"])
def get_variations():
    return jsonify(VARIATION_PROFILES)


@app.route("/process", methods=["POST"])
def process_video():
    if "video" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["video"]
    selected_ids = request.form.get("variations", "")
    selected_ids = [v.strip() for v in selected_ids.split(",") if v.strip()]
    if not selected_ids:
        selected_ids = [p["id"] for p in VARIATION_PROFILES]

    profiles = [p for p in VARIATION_PROFILES if p["id"] in selected_ids]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ext = Path(file.filename).suffix or ".mp4"
        input_path = str(tmp / f"original{ext}")
        file.save(input_path)

        output_files = []
        for i, profile in enumerate(profiles):
            out_name = f"variacao_{i+1:02d}_{profile['id']}.mp4"
            out_path = str(tmp / out_name)
            if apply_variation(input_path, out_path, profile):
                output_files.append((out_path, out_name))

        if not output_files:
            return jsonify({"error": "Nenhuma variação gerada"}), 500

        zip_path = str(tmp / "variacoes_portalcred.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, name in output_files:
                if Path(path).exists():
                    zf.write(path, name)

        return send_file(zip_path, as_attachment=True, download_name="variacoes_portalcred.zip", mimetype="application/zip")


if __name__ == "__main__":
    print(f"🎬 PortalCred Video Variator — porta {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
