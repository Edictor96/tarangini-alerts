# main.py
import os
import json
import logging
import math
import traceback
from typing import Optional, List, Any
from datetime import datetime

from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, create_engine, Session, select

# ---------------- logging ----------------
LOGFILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOGFILE), logging.StreamHandler()]
)
logger = logging.getLogger("alert-demo")

# store last error for quick UI access
last_error = {"time": None, "message": None, "trace": None}

# ---------------- app + DB ----------------
DB_FILE = "alerts.db"
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False, connect_args={"check_same_thread": False})
app = FastAPI(title="Disaster Alert Demo (robust)")
templates = Jinja2Templates(directory="templates")

# ---------------- models ----------------
class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    time: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

# ---------------- helpers ----------------
def set_last_error(exc: Exception):
    global last_error
    last_error = {
        "time": datetime.utcnow().isoformat(),
        "message": str(exc),
        "trace": traceback.format_exc()
    }
    logger.error("Last error set: %s", last_error["message"])
    logger.error(last_error["trace"])

def recreate_db():
    """Delete DB file and recreate tables."""
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            logger.info("Removed existing DB file: %s", DB_FILE)
        SQLModel.metadata.create_all(engine)
        logger.info("Created new DB (tables).")
        return True, "DB recreated"
    except Exception as e:
        set_last_error(e)
        return False, str(e)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ---------------- start-up ----------------
@app.on_event("startup")
def on_startup():
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("DB tables ready (using %s).", DB_FILE)
    except Exception as e:
        set_last_error(e)

# ---------------- load JSON safely ----------------
def load_alerts_from_json(file_path: str = "alerts.json"):
    """
    Clear DB and insert alerts from JSON file.
    JSON should be a list of objects:
      { "title": "...", "message": "...", "severity": "warning", "source":"INCOIS", "lat": 12.3, "lng": 78.9 }
    """
    inserted = 0
    skipped = 0
    skipped_details: List[str] = []
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found in cwd: {os.getcwd()}")

        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        if not isinstance(data, list):
            raise ValueError("alerts.json must contain a JSON array (list) of alert objects.")

        with Session(engine) as session:
            # clear table
            session.query(Alert).delete()
            session.commit()

            for idx, item in enumerate(data):
                # basic validation and coercion
                try:
                    title = item.get("title")
                    message = item.get("message")
                    severity = item.get("severity", "info")
                    source = item.get("source", "unknown")
                    lat = item.get("lat", None)
                    lng = item.get("lng", None)

                    # all alerts must have title & message
                    if not title or not message:
                        skipped += 1
                        skipped_details.append(f"idx {idx}: missing title/message")
                        continue

                    # if lat/lng provided, coerce to floats
                    if lat is not None and lng is not None:
                        try:
                            lat = float(lat)
                            lng = float(lng)
                        except Exception:
                            skipped += 1
                            skipped_details.append(f"idx {idx}: invalid lat/lng")
                            continue

                    alert = Alert(
                        title=str(title),
                        message=str(message),
                        severity=str(severity),
                        source=str(source),
                        time=datetime.utcnow(),
                        lat=lat,
                        lng=lng
                    )
                    session.add(alert)
                    inserted += 1
                except Exception as e_inner:
                    skipped += 1
                    skipped_details.append(f"idx {idx}: exception {e_inner}")
            session.commit()
        logger.info("Loaded alerts.json: inserted=%d skipped=%d", inserted, skipped)
        return {"inserted": inserted, "skipped": skipped, "skipped_details": skipped_details}
    except Exception as e:
        set_last_error(e)
        return {"error": str(e), "trace": last_error.get("trace")}

# ---------------- routes ----------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Show web UI (uses DB rows)."""
    try:
        # keep DB in sync with file each page load (safe)
        load_alerts_from_json("alerts.json")
    except Exception as e:
        logger.warning("home: load_alerts_from_json failed: %s", e)
    with Session(engine) as session:
        stmt = select(Alert).order_by(Alert.time.desc())
        alerts = session.exec(stmt).all()
    return templates.TemplateResponse("index.html", {"request": request, "alerts": alerts})

@app.get("/alerts", response_class=JSONResponse)
def api_alerts():
    """Return raw DB alerts as JSON."""
    try:
        load_result = load_alerts_from_json("alerts.json")
        with Session(engine) as session:
            stmt = select(Alert).order_by(Alert.time.desc())
            alerts = session.exec(stmt).all()
            return [a.dict() for a in alerts]
    except Exception as e:
        set_last_error(e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/alerts-nearby", response_class=JSONResponse)
def alerts_nearby(lat: float = Query(...), lng: float = Query(...), radius_km: float = 200.0):
    """Return alerts within radius_km of (lat,lng). Alerts without lat/lng are ignored."""
    try:
        load_alerts_from_json("alerts.json")
        with Session(engine) as session:
            stmt = select(Alert)
            alerts = session.exec(stmt).all()

        nearby = []
        for a in alerts:
            if a.lat is None or a.lng is None:
                continue
            try:
                dist = haversine_km(lat, lng, a.lat, a.lng)
            except Exception:
                continue
            if dist <= radius_km:
                row = a.dict()
                row["distance_km"] = round(dist, 2)
                nearby.append(row)
        return nearby
    except Exception as e:
        set_last_error(e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/reload")
def reload_json():
    """Manual reload: load alerts.json into DB and return summary."""
    res = load_alerts_from_json("alerts.json")
    return res

@app.get("/reset-db")
def reset_db():
    ok, msg = recreate_db()
    if not ok:
        return JSONResponse({"ok": False, "message": msg}, status_code=500)
    return {"ok": True, "message": msg}

@app.get("/last-error")
def show_last_error():
    """Return last logged exception (time/message)."""
    return last_error or {"time": None, "message": None, "trace": None}

# db viewing (simple table)
@app.get("/db-view", response_class=HTMLResponse)
def db_view(request: Request):
    try:
        load_alerts_from_json("alerts.json")
    except Exception:
        pass
    with Session(engine) as session:
        stmt = select(Alert).order_by(Alert.time.desc())
        alerts = session.exec(stmt).all()
    return templates.TemplateResponse("db_view.html", {"request": request, "alerts": alerts, "columns": None, "rows": None})

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")