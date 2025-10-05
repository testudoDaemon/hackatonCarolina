import os
import json
import time
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from cachetools import TTLCache


# -------------------------------
# Helpers y constantes (nivel módulo)
# -------------------------------

# --- AQI helper (PM2.5) US EPA ---
PM25_BREAKPOINTS = [
    (0.0,   12.0,    0,   50,  "Good"),
    (12.1,  35.4,   51,  100,  "Moderate"),
    (35.5,  55.4,  101,  150,  "Unhealthy for Sensitive Groups"),
    (55.5, 150.4,  151,  200,  "Unhealthy"),
    (150.5, 250.4, 201,  300,  "Very Unhealthy"),
    (250.5, 350.4, 301,  400,  "Hazardous"),
    (350.5, 500.4, 401,  500,  "Hazardous"),
]

# --- AQI helper (PM10) US EPA ---
PM10_BREAKPOINTS = [
    (0,    54,    0,   50,  "Good"),
    (55,   154,  51,  100,  "Moderate"),
    (155,  254, 101,  150,  "Unhealthy for Sensitive Groups"),
    (255,  354, 151,  200,  "Unhealthy"),
    (355,  424, 201,  300,  "Very Unhealthy"),
    (425,  504, 301,  400,  "Hazardous"),
    (505,  604, 401,  500,  "Hazardous"),
]


def pm25_to_aqi(pm25: float):
    for C_lo, C_hi, I_lo, I_hi, category in PM25_BREAKPOINTS:
        if C_lo <= pm25 <= C_hi:
            aqi = (I_hi - I_lo) / (C_hi - C_lo) * (pm25 - C_lo) + I_lo
            return round(aqi), category
    return 500, "Hazardous"


def pm10_to_aqi(pm10: float):
    for C_lo, C_hi, I_lo, I_hi, category in PM10_BREAKPOINTS:
        if C_lo <= pm10 <= C_hi:
            aqi = (I_hi - I_lo) / (C_hi - C_lo) * (pm10 - C_lo) + I_lo
            return round(aqi), category
    return 500, "Hazardous"


def safe_mean(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None


def aqi_percent(aqi: float) -> float:
    """Porcentaje del AQI respecto al máximo 500 (US EPA)."""
    pct = (aqi / 500.0) * 100.0
    return round(max(0.0, min(100.0, pct)), 2)


def extract_field_value(pa_json, field_name: str):
    """
    Soporta dos formatos típicos de PurpleAir:
    1) { "sensor": { "<field>": value, ... } }
    2) { "fields": [...], "data": [[...]] }
    """
    if not pa_json:
        return None

    # Forma objeto
    if isinstance(pa_json, dict) and "sensor" in pa_json and isinstance(pa_json["sensor"], dict):
        if field_name in pa_json["sensor"]:
            try:
                return float(pa_json["sensor"][field_name])
            except (TypeError, ValueError):
                return None

    # Forma fields+data
    if isinstance(pa_json, dict) and "fields" in pa_json and "data" in pa_json:
        try:
            fields = pa_json["fields"]
            idx = fields.index(field_name)
            return float(pa_json["data"][0][idx])
        except Exception:
            return None

    return None


def build_field(base: str, variant: str = "atm", channel_suffix: str = "") -> str:
    """
    base: "pm1.0", "pm2.5", "pm10.0"
    variant: "atm" o "cf_1"
    channel_suffix: "", "_a", "_b"
    """
    if variant not in ("atm", "cf_1"):
        variant = "atm"
    if channel_suffix not in ("", "_a", "_b"):
        channel_suffix = ""
    return f"{base}_{variant}{channel_suffix}"


# Logging temprano (antes de crear app)
logging.basicConfig(level=logging.INFO)
load_dotenv()


# -------------------------------
# Factory de la app y rutas
# -------------------------------
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
    STREAM_INTERVAL = int(os.getenv("STREAM_INTERVAL", "1"))

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
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Campos permitidos (whitelist opcional) SOLO para /api/sensor-data
    allowed_fields = {
        "pm2.5", "pm2_5", "pm10.0", "pm10_0", "pm1.0", "pm1_0",
        "humidity", "temperature", "pressure", "voc", "ozone1", "ozone2", "aqi",
    }

    def sanitize_fields(query_fields):
        if not query_fields:
            return None
        req = [f.strip() for f in query_fields.split(",") if f.strip()]
        if not req:
            return None
        whitelisted = [f for f in req if f in allowed_fields]
        return ",".join(whitelisted) if whitelisted else None

    def fetch_purpleair(fields: str | None):
        """Lee de cache si existe; si no, consulta PurpleAir con headers y timeout."""
        cache_key = f"pa::{fields or 'ALL'}"
        if cache_key in cache:
            return cache[cache_key]

        headers = {"X-API-Key": PA_KEY}
        params = {}
        if fields:
            params["fields"] = fields

        try:
            r = session.get(PA_URL, headers=headers, params=params, timeout=PA_TIMEOUT)
            if r.status_code in (401, 403):
                app.logger.error(f"PurpleAir auth error: {r.status_code} {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            cache[cache_key] = data
            return data
        except requests.RequestException as e:
            app.logger.exception("Error consultando PurpleAir")
            return {"error": "purpleair_unreachable", "detail": str(e)}

    # ---------- Rutas ----------
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
            # Nota: mantener este generador liviano
            while True:
                data = fetch_purpleair(fields)
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(STREAM_INTERVAL)

        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # evitar buffering en proxies
        }
        return Response(event_stream(), mimetype="text/event-stream", headers=headers)

    @app.get("/api/pm1")
    def api_pm1():
        variant = request.args.get("variant", "atm")
        channel = request.args.get("channel", "")  # "", "_a", "_b"
        if channel not in ("", "_a", "_b"):
            channel = ""
        field = build_field("pm1.0", variant, channel)

        data = fetch_purpleair(field)
        value = extract_field_value(data, field)
        if value is None:
            return jsonify({"error": "field_not_found_or_null", "field": field}), 400

        # PM1.0 no tiene AQI oficial → aproximación con PM2.5 (opcional).
        aqi_val, category = pm25_to_aqi(value)
        pct = aqi_percent(aqi_val)

        return jsonify({
            "field": field,
            "pm": value,
            "aqi": aqi_val,
            "aqi_percent": pct,
            "category": category,
        })

    @app.get("/api/pm25")
    def api_pm25():
        variant = request.args.get("variant", "atm")  # atm (exterior) o cf_1 (interior)
        channel = request.args.get("channel", "")     # "", "_a", "_b"
        if channel not in ("", "_a", "_b"):
            channel = ""
        field = build_field("pm2.5", variant, channel)

        data = fetch_purpleair(field)
        value = extract_field_value(data, field)
        if value is None:
            return jsonify({"error": "field_not_found_or_null", "field": field}), 400

        aqi_val, category = pm25_to_aqi(value)
        pct = aqi_percent(aqi_val)

        return jsonify({
            "field": field,
            "pm": value,
            "aqi": aqi_val,
            "aqi_percent": pct,
            "category": category,
        })

    @app.get("/api/pm10")
    def api_pm10():
        variant = request.args.get("variant", "atm")
        channel = request.args.get("channel", "")
        if channel not in ("", "_a", "_b"):
            channel = ""
        field = build_field("pm10.0", variant, channel)

        data = fetch_purpleair(field)
        value = extract_field_value(data, field)
        if value is None:
            return jsonify({"error": "field_not_found_or_null", "field": field}), 400

        # Aquí devolvemos solo PM. (Si quieres AQI PM10 ya está implementado como helper)
        return jsonify({
            "field": field,
            "pm": value,
            "aqi": None,
            "aqi_percent": None,
            "category": None,
        })

    @app.get("/api/aqi/combined")
    def aqi_combined():
        variant = request.args.get("variant", "atm")
        channel = request.args.get("channel", "")
        if channel not in ("", "_a", "_b"):
            channel = ""

        f_pm1  = build_field("pm1.0",  variant, channel)
        f_pm25 = build_field("pm2.5",  variant, channel)
        f_pm10 = build_field("pm10.0", variant, channel)
        fields = ",".join([f_pm1, f_pm25, f_pm10])

        data = fetch_purpleair(fields)
        v_pm1  = extract_field_value(data, f_pm1)
        v_pm25 = extract_field_value(data, f_pm25)
        v_pm10 = extract_field_value(data, f_pm10)

        # Sub-AQIs
        subindices = []
        det = {}

        if v_pm25 is not None:
            aqi25, cat25 = pm25_to_aqi(v_pm25)
            det["pm25"] = {
                "pm": v_pm25, "aqi": aqi25, "category": cat25,
                "percent": aqi_percent(aqi25)
            }
            subindices.append(("pm25", aqi25, cat25))
        else:
            det["pm25"] = {"pm": None, "aqi": None, "category": None, "percent": None}

        if v_pm10 is not None:
            aqi10, cat10 = pm10_to_aqi(v_pm10)
            det["pm10"] = {
                "pm": v_pm10, "aqi": aqi10, "category": cat10,
                "percent": aqi_percent(aqi10)
            }
            subindices.append(("pm10", aqi10, cat10))
        else:
            det["pm10"] = {"pm": None, "aqi": None, "category": None, "percent": None}

        # PM1.0: aproximación usando PM2.5 (no oficial)
        if v_pm1 is not None:
            aqi1, cat1 = pm25_to_aqi(v_pm1)
            det["pm1"] = {
                "pm": v_pm1, "aqi": aqi1, "category": cat1,
                "percent": aqi_percent(aqi1),
                "note": "approx_from_pm25_breakpoints",
            }
            subindices.append(("pm1", aqi1, cat1))
        else:
            det["pm1"] = {"pm": None, "aqi": None, "category": None, "percent": None}

        # AQI combinado: máximo sub-índice disponible
        if subindices:
            top = max(subindices, key=lambda t: t[1])  # (name, aqi, category)
            combined_aqi = top[1]
            combined_category = top[2]
            combined_from = top[0]
            combined_percent = aqi_percent(combined_aqi)
        else:
            combined_aqi = combined_category = combined_from = combined_percent = None

        avg_pm = safe_mean([v_pm1, v_pm25, v_pm10])

        return jsonify({
            "fields": {"pm1": f_pm1, "pm25": f_pm25, "pm10": f_pm10},
            "values": {"pm1": v_pm1, "pm25": v_pm25, "pm10": v_pm10, "pm_avg": avg_pm},
            "subindices": det,
            "combined": {
                "aqi": combined_aqi,
                "percent": combined_percent,
                "category": combined_category,
                "from": combined_from  # cuál PM determinó el AQI
            }
        })

    return app


app = create_app()

if __name__ == "__main__":
    # Solo para desarrollo. En producción usa gunicorn.
    port = int(os.getenv("API_PORT", "7777"))
    app.run(host="0.0.0.0", port=port)
