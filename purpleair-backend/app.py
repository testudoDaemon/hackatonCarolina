import os, json, time, logging, csv
from io import StringIO
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, make_response
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

    # -------- Rate limiting --------
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["60 per minute"]
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

    # -------- Cache --------
    cache = TTLCache(maxsize=128, ttl=CACHE_TTL)

    # -------- Sesión requests con reintentos --------
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

    # -------- Campos permitidos --------
    allowed_fields = {
        "pm2.5", "pm2_5", "pm10.0", "pm10_0", "pm1.0", "pm1_0", "humidity",
        "temperature", "pressure", "voc", "ozone1", "ozone2", "aqi"
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
        """Lee de cache si existe, si no, llama PurpleAir con headers y timeout."""
        cache_key = f"pa::{fields or 'ALL'}"
        if cache_key in cache:
            return cache[cache_key]

        headers = {"X-API-Key": PA_KEY}
        params = {}
        if fields:
            params["fields"] = fields

        try:
            r = session.get(PA_URL, headers=headers, params=params, timeout=PA_TIMEOUT)
            if r.status_code in [401, 403]:
                app.logger.error(f"PurpleAir auth error: {r.status_code} {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            cache[cache_key] = data
            return data
        except requests.RequestException as e:
            app.logger.exception("Error consultando PurpleAir")
            return {"error": "purpleair_unreachable", "detail": str(e)}

    # -------- Endpoints básicos --------

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
    @limiter.limit("10 per minute")
    def sensor_stream():
        fields = sanitize_fields(request.args.get("fields"))

        def event_stream():
            while True:
                data = fetch_purpleair(fields)
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(STREAM_INTERVAL)

        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
        return Response(event_stream(), mimetype="text/event-stream", headers=headers)

    # -------- Nuevo endpoint: Exportar CSV --------

    @app.get("/api/sensor-data/csv")
    def export_csv():
        # 1️⃣ Obtener campos opcionales
        fields = sanitize_fields(request.args.get("fields"))
        data = fetch_purpleair(fields)

        # 2️⃣ Crear un buffer temporal
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)

        # 3️⃣ Escribir encabezados
        writer.writerow(["Campo", "Valor"])

        # 4️⃣ Escribir datos
        sensor = data.get("sensor", {})
        if not sensor:
            writer.writerow(["Error", "No se encontraron datos del sensor"])
        else:
            for key, value in sensor.items():
                if isinstance(value, (str, int, float)):
                    writer.writerow([key, value])
                elif isinstance(value, dict):
                    for subkey, subval in value.items():
                        writer.writerow([f"{key}.{subkey}", subval])

        # 5️⃣ Devolver el CSV como descarga
        response = make_response(csv_buffer.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=sensor_data.csv"
        response.headers["Content-Type"] = "text/csv"
        return response

    # -------- Logging --------
    logging.basicConfig(level=logging.INFO)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "7777"))
    app.run(host="0.0.0.0", port=port)
