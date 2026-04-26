
import logging
import os
import shutil
import uvicorn  # type: ignore
from datetime import datetime
from fastapi import FastAPI, Request, Response, UploadFile, File  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
import importlib
import sys
# Inject current directory into path for Render
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())
try:
    pdfplumber = importlib.import_module("pdfplumber")
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    pdfplumber = None
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("JudiQ-API")

app = FastAPI(
    title="JudiQ Legal AI API",
    version="7.0.0",
    description="Court-ready legal intelligence platform for Section 138 NI Act cases."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.options("/analyze")
async def analyze_options():
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept",
    })

@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    })


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    import os
    from database_manager import DatabaseManager
    
    # ── Diagnostic Audit ───────────────────────────────────────────────────
    cwd = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"DIAGNOSTIC: CWD={cwd}")
    logger.info(f"DIAGNOSTIC: SCRIPT_DIR={script_dir}")
    try:
        logger.info(f"FILES in CWD: {os.listdir(cwd)}")
        logger.info(f"FILES in SCRIPT_DIR: {os.listdir(script_dir)}")
    except Exception as ex:
        logger.error(f"DIAGNOSTIC FAILED: {ex}")
    # ────────────────────────────────────────────────────────────────────────

    try:
        DatabaseManager.init_db()
        logger.info("✅ JudiQ Backend Started | Database Initialized")
    except Exception as e:
        logger.error(f"⚠️  Database initialization failed: {e} — continuing without persistence.")


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/")
async def health():
    import os
    files = os.listdir(".")
    return {
        "status": "operational",
        "version": "7.0.0",
        "files_in_root": files,
        "cwd": os.getcwd(),
        "timestamp": datetime.now().isoformat()
    }


# ── Analyze ────────────────────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze(request: Request):
    request_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    logger.info(f"[{request_id}] /analyze request received")

    # ── Parse body ─────────────────────────────────────────────────────────────
    try:
        raw_data = await request.json()
    except Exception as e:
        logger.warning(f"[{request_id}] JSON parse failed: {e}")
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Invalid JSON body.",
            "error_code": "INVALID_JSON",
            "user_message": "The request could not be read. Please refresh and try again."
        })

    from engine_core import JudiQEngine
    from normalizer import normalize_input, validate_minimum_viability, ValidationError
    from database_manager import DatabaseManager

    # ── Minimum viability gate ─────────────────────────────────────────────────
    try:
        validate_minimum_viability(raw_data)
    except ValidationError as ve:
        logger.warning(f"[{request_id}] Validation failed: {ve.message}")
        return JSONResponse(status_code=422, content={
            "success": False,
            "error": ve.message,
            "error_code": "VALIDATION_ERROR",
            "field": ve.field,
            "user_message": ve.message
        })

    # ── Engine execution ───────────────────────────────────────────────────────
    try:
        result = JudiQEngine.analyze_case(raw_data)
    except ValidationError as ve:
        return JSONResponse(status_code=422, content={
            "success": False,
            "error": ve.message,
            "error_code": "VALIDATION_ERROR",
            "user_message": ve.message
        })
    except Exception as e:
        logger.error(f"[{request_id}] Engine error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "The analysis engine encountered an internal error.",
            "error_code": "ENGINE_ERROR",
            "user_message": "Analysis failed. Please try again or contact support.",
            "detail": str(e)
        })

    # ── Persist (non-fatal) ────────────────────────────────────────────────────
    try:
        # Use the result from the engine which is already normalized
        uid = result.get("metadata", {}).get("user_id", "ANONYMOUS")
        cid = result.get("case_id", "")
        if uid and cid and uid != "ANONYMOUS":
            case_data = result.get("case_data", {})
            DatabaseManager.save_case(
                cid, 
                uid, 
                case_data, 
                result, 
                result.get("score", 0), 
                result.get("verdict", "Unknown")
            )
            # --- AUTO-INITIALIZE CASEROOM ---
            from caseroom_logic import CaseroomManager
            # Check if caseroom already exists to avoid duplicates
            existing_room_id = DatabaseManager.get_caseroom_by_case_id(cid)
            if not existing_room_id:
                CaseroomManager.initialize_caseroom_for_case(cid, uid)
    except Exception as e:
        logger.warning(f"[{request_id}] DB/Caseroom persistence failed (non-fatal): {e}")

    # ── Build response ─────────────────────────────────────────────────────────
    # Spread all result fields to the top level AND keep 'data' for compatibility
    response_body = {"success": True, "request_id": request_id}
    response_body.update(result)          # spread: score, verdict, draft, etc. at top level
    
    # Include Caseroom ID if it exists
    from database_manager import DatabaseManager
    response_body["caseroom_id"] = DatabaseManager.get_caseroom_by_case_id(cid)
    
    response_body["data"] = result        # keep nested copy for any legacy consumers
    return response_body


# ── Caseroom Management ────────────────────────────────────────────────────────
@app.post("/caseroom/create")
async def create_caseroom(request: Request):
    from caseroom_logic import CaseroomManager
    data = await request.json()
    cid = data.get("case_id")
    uid = data.get("user_id")
    room_id = CaseroomManager.initialize_caseroom_for_case(cid, uid)
    return {"success": True, "caseroom_id": room_id}

@app.get("/caseroom/{room_id}")
async def get_caseroom(room_id: str):
    from caseroom_logic import CaseroomManager
    data = CaseroomManager.get_full_caseroom_state(room_id)
    if not data: return JSONResponse(status_code=404, content={"error": "Room not found"})
    return {"success": True, "data": data}

@app.post("/caseroom/{room_id}/invite")
async def invite_to_caseroom(room_id: str, request: Request):
    from caseroom_logic import CaseroomManager
    data = await request.json()
    success = CaseroomManager.invite_collaborator(room_id, data.get("user_id"), data.get("role"))
    return {"success": success}

@app.post("/caseroom/{room_id}/message")
async def send_caseroom_message(room_id: str, request: Request):
    from caseroom_logic import CaseroomManager
    data = await request.json()
    success = CaseroomManager.post_comment(room_id, data.get("user_id"), data.get("content"))
    return {"success": success}

@app.post("/caseroom/{room_id}/task")
async def add_caseroom_task(room_id: str, request: Request):
    from caseroom_logic import CaseroomManager
    data = await request.json()
    success = CaseroomManager.add_milestone(room_id, data.get("title"), data.get("due_date"), data.get("description", ""))
    return {"success": success}
@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    from pdf_generator import PDFGenerator
    try:
        data = await request.json()
        pdf_bytes = PDFGenerator.generate_report(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=JudiQ_Legal_Report.pdf"}
        )
    except Exception as e:
        logger.error(f"PDF error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
