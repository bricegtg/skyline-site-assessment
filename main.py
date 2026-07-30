"""
Skyline Site Assessment — FastAPI backend
==========================================
Service-specific on-site assessment questionnaires, photo/video attachments,
branded PDF generation, and auto-creation of a linked CRM deal.
"""

import os
import io
import json
import uuid
import logging
import traceback
from datetime import datetime, timezone, timedelta, date

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

import schemas

# ─── Configuration ───────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")
CRM_BASE_URL = os.getenv("CRM_BASE_URL", "https://skyline-drones-crm.onrender.com")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/var/data/uploads")
VERSION = os.getenv("VERSION", "1.0.0")

PHT = timezone(timedelta(hours=8))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("skyline-site-assessment")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Skyline Site Assessment")

db_pool: asyncpg.Pool | None = None


# ─── Database setup ──────────────────────────────────────────────────────────
async def init_db():
    global db_pool
    if not DATABASE_URL:
        logger.warning("No DATABASE_URL configured — running without database")
        return
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                  id           SERIAL PRIMARY KEY,
                  service_id   TEXT NOT NULL,
                  status       TEXT NOT NULL DEFAULT 'draft',
                  data         JSONB NOT NULL DEFAULT '{}'::jsonb,
                  property_name    TEXT,
                  contact_name     TEXT,
                  contact_email    TEXT,
                  assessor         TEXT,
                  crm_deal_id      INTEGER,
                  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  submitted_at TIMESTAMPTZ
                );
                """
            )
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_assessments_service ON assessments(service_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_assessments_status  ON assessments(status);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created_at DESC);")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessment_attachments (
                  id            SERIAL PRIMARY KEY,
                  assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
                  filename      TEXT NOT NULL,
                  original_name TEXT,
                  mime_type     TEXT,
                  size_bytes    INTEGER,
                  section_id    TEXT,
                  caption       TEXT,
                  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        db_pool = None


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.on_event("shutdown")
async def on_shutdown():
    if db_pool:
        await db_pool.close()


def require_db():
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def row_to_dict(row) -> dict:
    d = dict(row)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, str) and k == "data":
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    if isinstance(d.get("data"), str):
        try:
            d["data"] = json.loads(d["data"])
        except Exception:
            d["data"] = {}
    return d


def estimate_value(service_id: str, data: dict) -> float:
    """Best-effort estimated value derived from area x rate, else 0."""
    try:
        if service_id == "facade_cleaning":
            area = float(data.get("facade_area_sqm") or 0)
            return round(area * 45, 2)  # PHP/sqm rough benchmark
        if service_id == "roof_leak_inspection":
            area = float(data.get("roof_area_sqm") or 0)
            return round(area * 25, 2)
        if service_id == "aerial_imaging":
            hectares = float(data.get("coverage_hectares") or 0)
            return round(hectares * 5000, 2) if hectares else 15000.0
        if service_id == "firefighting_equipment":
            return 0.0
    except Exception:
        pass
    return 0.0


async def create_crm_deal(assessment: dict, base_url_for_pdf: str) -> int | None:
    service = schemas.SERVICE_BY_ID.get(assessment["service_id"])
    service_name = service["name"] if service else assessment["service_id"]
    data = assessment.get("data") or {}
    property_name = data.get("property_name") or assessment.get("property_name") or "Untitled Property"
    contact_name = data.get("primary_contact_name") or assessment.get("contact_name") or ""
    org = data.get("billing_entity") or property_name
    urgency = data.get("urgency_level") or ""
    priority = "High" if urgency.startswith("Rush") else "Medium"
    target_date = data.get("target_service_date")
    if target_date:
        close_date = target_date
    else:
        close_date = (datetime.now(PHT) + timedelta(days=30)).date().isoformat()
    today = datetime.now(PHT).date().isoformat()
    value = estimate_value(assessment["service_id"], data)

    payload = {
        "name": f"{property_name} — {service_name}",
        "contact": contact_name,
        "org": org,
        "value": value,
        "currency": "PHP",
        "stage": "Site Assessed",
        "priority": priority,
        "owner": "Brice Adler",
        "created": today,
        "closeDate": close_date,
        "probability": 40,
        "notes": f"Created from Site Assessment #{assessment['id']}. Service: {service_name}. "
                 f"See PDF: {base_url_for_pdf}/api/assessments/{assessment['id']}/pdf",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{CRM_BASE_URL}/api/deals", json=payload)
            if resp.status_code == 200:
                body = resp.json()
                return body.get("id")
            else:
                logger.warning(f"CRM deal creation failed: {resp.status_code} {resp.text[:300]}")
    except Exception as e:
        logger.warning(f"CRM deal creation error (non-fatal): {e}")
    return None


# ─── Static files ────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")


# ─── Health & schema endpoints ───────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"ok": True, "service": "skyline-site-assessment", "version": VERSION}


@app.get("/api/schemas")
async def get_schemas():
    return schemas.SERVICES


@app.get("/api/services")
async def get_services():
    return schemas.service_summary()


# ─── Assessments CRUD ────────────────────────────────────────────────────────

@app.post("/api/assessments")
async def create_assessment(payload: dict):
    require_db()
    service_id = payload.get("service_id")
    if service_id not in schemas.SERVICE_BY_ID:
        raise HTTPException(status_code=400, detail="Invalid service_id")
    assessor = payload.get("assessor") or "Brice Adler"
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO assessments (service_id, status, data, assessor)
            VALUES ($1, 'draft', '{}'::jsonb, $2)
            RETURNING *
            """,
            service_id, assessor,
        )
    return row_to_dict(row)


@app.get("/api/assessments")
async def list_assessments(service_id: str | None = None, status: str | None = None,
                            search: str | None = None, limit: int = 100, offset: int = 0):
    require_db()
    clauses = []
    params = []
    idx = 1
    if service_id:
        clauses.append(f"service_id = ${idx}")
        params.append(service_id)
        idx += 1
    if status:
        clauses.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if search:
        clauses.append(f"(property_name ILIKE ${idx} OR contact_name ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    params.append(offset)
    query = f"""
        SELECT *, COUNT(*) OVER() AS total_count
        FROM assessments
        {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    items = [row_to_dict(r) for r in rows]
    total = items[0]["total_count"] if items else 0
    for it in items:
        it.pop("total_count", None)
    return {"items": items, "total": total}


@app.get("/api/assessments/{aid}")
async def get_assessment(aid: int):
    require_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assessments WHERE id = $1", aid)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        attachments = await conn.fetch(
            "SELECT * FROM assessment_attachments WHERE assessment_id = $1 ORDER BY created_at ASC", aid
        )
    result = row_to_dict(row)
    result["attachments"] = [row_to_dict(a) for a in attachments]
    return result


@app.patch("/api/assessments/{aid}")
async def update_assessment(aid: int, payload: dict):
    require_db()
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM assessments WHERE id = $1", aid)
        if not existing:
            raise HTTPException(status_code=404, detail="Not found")

        set_clauses = ["updated_at = NOW()"]
        params = []
        idx = 1

        if "data" in payload and isinstance(payload["data"], dict):
            current_data = json.loads(existing["data"]) if isinstance(existing["data"], str) else (existing["data"] or {})
            merged = {**current_data, **payload["data"]}
            set_clauses.append(f"data = ${idx}::jsonb")
            params.append(json.dumps(merged))
            idx += 1
            # Denormalize for fast listing
            if "property_name" in merged:
                set_clauses.append(f"property_name = ${idx}")
                params.append(merged.get("property_name"))
                idx += 1
            if "primary_contact_name" in merged:
                set_clauses.append(f"contact_name = ${idx}")
                params.append(merged.get("primary_contact_name"))
                idx += 1
            if "primary_contact_email" in merged:
                set_clauses.append(f"contact_email = ${idx}")
                params.append(merged.get("primary_contact_email"))
                idx += 1

        for field in ["status", "property_name", "contact_name", "contact_email", "assessor"]:
            if field in payload and field != "data":
                set_clauses.append(f"{field} = ${idx}")
                params.append(payload[field])
                idx += 1

        params.append(aid)
        query = f"UPDATE assessments SET {', '.join(set_clauses)} WHERE id = ${idx} RETURNING *"
        row = await conn.fetchrow(query, *params)
    return row_to_dict(row)


@app.delete("/api/assessments/{aid}")
async def delete_assessment(aid: int):
    require_db()
    async with db_pool.acquire() as conn:
        attachments = await conn.fetch("SELECT * FROM assessment_attachments WHERE assessment_id = $1", aid)
        for a in attachments:
            path = os.path.join(UPLOAD_DIR, str(aid), a["filename"])
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove file {path}: {e}")
        result = await conn.execute("DELETE FROM assessments WHERE id = $1", aid)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@app.post("/api/assessments/{aid}/duplicate")
async def duplicate_assessment(aid: int):
    require_db()
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM assessments WHERE id = $1", aid)
        if not existing:
            raise HTTPException(status_code=404, detail="Not found")
        row = await conn.fetchrow(
            """
            INSERT INTO assessments (service_id, status, data, property_name, contact_name, contact_email, assessor)
            VALUES ($1, 'draft', $2, $3, $4, $5, $6)
            RETURNING *
            """,
            existing["service_id"], existing["data"], existing["property_name"],
            existing["contact_name"], existing["contact_email"], existing["assessor"],
        )
    return row_to_dict(row)


# ─── Submit (PDF + CRM deal) ─────────────────────────────────────────────────

@app.post("/api/assessments/{aid}/submit")
async def submit_assessment(aid: int, request: Request):
    require_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assessments WHERE id = $1", aid)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        attachments = await conn.fetch(
            "SELECT * FROM assessment_attachments WHERE assessment_id = $1 ORDER BY created_at ASC", aid
        )
        submitted_row = await conn.fetchrow(
            """
            UPDATE assessments SET status = 'submitted', submitted_at = NOW(), updated_at = NOW()
            WHERE id = $1 RETURNING *
            """,
            aid,
        )
    assessment = row_to_dict(submitted_row)
    assessment["attachments"] = [row_to_dict(a) for a in attachments]

    base_url = str(request.base_url).rstrip("/")
    crm_deal_id = await create_crm_deal(assessment, base_url)

    if crm_deal_id:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE assessments SET crm_deal_id = $1 WHERE id = $2", crm_deal_id, aid)

    pdf_url = f"{base_url}/api/assessments/{aid}/pdf"
    return {"pdf_url": pdf_url, "crm_deal_id": crm_deal_id, "status": "submitted"}


# ─── Attachments ─────────────────────────────────────────────────────────────

@app.post("/api/assessments/{aid}/attachments")
async def upload_attachments(aid: int, files: list[UploadFile] = File(...), section_id: str | None = None):
    require_db()
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM assessments WHERE id = $1", aid)
        if not existing:
            raise HTTPException(status_code=404, detail="Assessment not found")

    dest_dir = os.path.join(UPLOAD_DIR, str(aid))
    os.makedirs(dest_dir, exist_ok=True)

    created = []
    async with db_pool.acquire() as conn:
        for f in files:
            original_name = f.filename or "upload"
            unique_name = f"{uuid.uuid4().hex}_{original_name}"
            dest_path = os.path.join(dest_dir, unique_name)
            content = await f.read()
            with open(dest_path, "wb") as out:
                out.write(content)
            row = await conn.fetchrow(
                """
                INSERT INTO assessment_attachments
                  (assessment_id, filename, original_name, mime_type, size_bytes, section_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                aid, unique_name, original_name, f.content_type, len(content), section_id,
            )
            created.append(row_to_dict(row))
    return created


@app.get("/api/attachments/{attachment_id}")
async def get_attachment(attachment_id: int):
    require_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assessment_attachments WHERE id = $1", attachment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    path = os.path.join(UPLOAD_DIR, str(row["assessment_id"]), row["filename"])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=row["mime_type"] or "application/octet-stream",
                         filename=row["original_name"] or row["filename"])


@app.delete("/api/attachments/{attachment_id}")
async def delete_attachment(attachment_id: int):
    require_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assessment_attachments WHERE id = $1", attachment_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        path = os.path.join(UPLOAD_DIR, str(row["assessment_id"]), row["filename"])
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to remove file {path}: {e}")
        await conn.execute("DELETE FROM assessment_attachments WHERE id = $1", attachment_id)
    return {"ok": True}


# ─── PDF ──────────────────────────────────────────────────────────────────────

@app.get("/api/assessments/{aid}/pdf")
async def get_pdf(aid: int):
    require_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM assessments WHERE id = $1", aid)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        attachments = await conn.fetch(
            "SELECT * FROM assessment_attachments WHERE assessment_id = $1 ORDER BY created_at ASC", aid
        )
    assessment = row_to_dict(row)
    assessment["attachments"] = [row_to_dict(a) for a in attachments]

    import pdf_render
    pdf_bytes = pdf_render.render_pdf(assessment, UPLOAD_DIR)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="assessment-{aid}.pdf"'},
    )
