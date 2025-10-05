import os
import pathlib
from typing import Tuple

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import earthaccess


class SearchRequest(BaseModel):
    short_name: str = "ATL06"
    bounding_box: Tuple[float, float, float, float]
    temporal: Tuple[str, str]
    count: int = 10


app = FastAPI(title="EarthAccess demo API")

# Serve the simple static frontend
static_dir = pathlib.Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

DOWNLOAD_DIR = pathlib.Path(os.getenv("EARTHACCESS_DOWNLOAD_DIR", "./downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def login_noninteractive():
    """Attempt non-interactive login using environment variables, otherwise fall back to .netrc or interactive prompt."""
    user = os.environ.get("EARTHDATA_USERNAME")
    pwd = os.environ.get("EARTHDATA_PASSWORD")
    if user and pwd:
        earthaccess.login(username=user, password=pwd)
    else:
        # If no env vars, earthaccess will try .netrc or prompt the user
        earthaccess.login()


def result_to_jsonable(item):
    # Try to convert the result item to a plain dict; if that fails, fallback to string
    try:
        return dict(item)
    except Exception:
        try:
            return item.__dict__
        except Exception:
            return str(item)


@app.post("/search")
def search(req: SearchRequest):
    try:
        login_noninteractive()
        results = earthaccess.search_data(
            short_name=req.short_name,
            bounding_box=tuple(req.bounding_box),
            temporal=tuple(req.temporal),
            count=req.count,
        )

        out = [result_to_jsonable(r) for r in results]
        return {"count": len(out), "results": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download")
def download(req: SearchRequest):
    try:
        login_noninteractive()
        results = earthaccess.search_data(
            short_name=req.short_name,
            bounding_box=tuple(req.bounding_box),
            temporal=tuple(req.temporal),
            count=req.count,
        )

        if not results:
            return {"downloaded": []}

        outdir = DOWNLOAD_DIR / f"{req.short_name}"
        outdir.mkdir(parents=True, exist_ok=True)

        files = earthaccess.download(results, str(outdir))

        # Normalize to list of strings
        try:
            files_list = [str(f) for f in files]
        except Exception:
            files_list = [str(files)] if files else []

        return {"downloaded": files_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
