import os, json, time, logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from cachetools import TTLCache

load_dotenv()

def create_app():
    app = Flask(__name__)

    # -------- Seguridad básica (CORS) --------
    allowed_origins = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()
    ] or ["http://localhost:5173"]
    CORS(app, origins=allowed_origins)

    # -------- Rate limiting (evita abuso) --------
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["60 per minute"]  # ajusta según tus necesidades
    )

    # -------- Config PurpleAir --------
    PA_KEY = os.getenv("PURPLEAIR_API_KEY", "")
    SENSOR_INDEX = os.getenv("PURPLEAIR_SENSOR_INDEX", "")
    CACHE_TTL = int(os.getenv("CACHE_TTL", "20"))
    PA_TIMEOUT = int(os.getenv("PURPLEAIR_TIMEOUT", "5"))
    STREAM_INTERVAL = int(os.getenv("STREAM_INTERVAL", "10"))

    if not PA_KEY or not SENSOR_INDEX:
        raise RuntimeError("Faltan PURPLEAIR_API_KEY o PURPLEAIR_SENSOR_INDEX en .env")

    PA_URL = f"https://api.purpleair.com/v1/sensors/{SENSOR_INDEX}"

    # Cache en memoria
    cache = TTLCache(maxsize=128, ttl=CACHE_TTL)

    # Sesión requests con reintentos
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Campos permitidos (whitelist opcional)
    allowed_fields = {
        "pm2.5", "pm2_5", "pm10.0", "pm10_0", "pm1.0", "pm1_0", "humidity", "temperature",
        "pressure", "voc", "ozone1", "ozone2", "aqi"
    }

    def sanitize_fields(query_fields: str | None):
        if not query_fields:
            return None
        req = [f.strip() for f in query_fields.split(",") if f.strip()]
        if not req:
            return None
        whitelisted = [f for f in req if f in allowed_fields]
        return ",".join(whitelisted) if whitelisted else None

    def fetch_purpleair(fields: str | None):
        """
        Lee de cache si existe, si no, llama PurpleAir con headers y timeout.
        """
        cache_key = f"pa::{fields or 'ALL'}"
        if cache_key in cache:
            return cache[cache_key]

        headers = {"X-API-Key": PA_KEY}
        params = {}
        if fields:
            params["fields"] = fields

        try:
            r = session.get(PA_URL, headers=headers, params=params, timeout=PA_TIMEOUT)
            if r.status_code == 401 or r.status_code == 403:
                # Clave inválida o no permitida
                app.logger.error(f"PurpleAir auth error: {r.status_code} {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            cache[cache_key] = data
            return data
        except requests.RequestException as e:
            app.logger.exception("Error consultando PurpleAir")
            # Respuesta controlada para el frontend
            return {"error": "purpleair_unreachable", "detail": str(e)}

    @app.get("/health")
    @limiter.limit("10 per minute")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/sensor-data")
    @limiter.limit("30 per minute")
    def sensor_data():
        fields = sanitize_fields(request.args.get("fields"))
        data = fetch_purpleair(fields)
        return jsonify(data)

    @app.get("/api/sensor-data/stream")
    @limiter.limit("10 per minute")  # limita inicios de stream
    def sensor_stream():
        fields = sanitize_fields(request.args.get("fields"))

        def event_stream():
            # Nota: Mantén este generador liviano
            while True:
                data = fetch_purpleair(fields)
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(STREAM_INTERVAL)

        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # evitar buffering en reverse proxies; aquí por buenas prácticas
        }
        return Response(event_stream(), mimetype="text/event-stream", headers=headers)

    # Logging
    logging.basicConfig(level=logging.INFO)
    return app

app = create_app()

if __name__ == "__main__":
    # Solo para desarrollo. En producción usa gunicorn (ver más abajo).
    port = int(os.getenv("API_PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
