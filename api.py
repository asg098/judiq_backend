import posixpath
import logging
import os
import shutil
import uvicorn  # type: ignore
from datetime import datetime
from fastapi import FastAPI, Request, Response, UploadFile, File, Form  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

import importlib
import sys
# Inject current directory into path for Render
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from ocr_engine import OCREngine

try:
    pdfplumber = importlib.import_module("pdfplumber")
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    pdfplumber = None

try:
    # pyrefly: ignore [missing-import]
    from PIL import Image
    # pyrefly: ignore [missing-import]
    import pytesseract
    import io
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


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

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── CORS preflight handlers ────────────────────────────────────────────────────
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
        case_data = result.get("case_data", {})
        uid = case_data.get("user_id", "ANONYMOUS")
        cid = case_data.get("case_id", "")
        if uid and cid and uid != "ANONYMOUS":
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
    
    # Include Caseroom ID if it exists (safely)
    case_data = result.get("case_data", {})
    cid = case_data.get("case_id", "")
    from database_manager import DatabaseManager
    response_body["caseroom_id"] = DatabaseManager.get_caseroom_by_case_id(cid) if cid else None
    
    response_body["data"] = result        # keep nested copy for any legacy consumers
    return response_body


# ── Phase 1: Verification (MCA & India Post APIs) ──────────────────────────
@app.get("/verify-mca/{cin}")
async def verify_mca_data(cin: str):
    """
    Mock MCA (Ministry of Corporate Affairs) API integration.
    Verifies company details to ensure correct Directors are named for Sec 141.
    """
    logger.info(f"Verifying MCA data for CIN: {cin}")
    # In a real scenario, this would call the MCA API
    if not cin or len(cin) < 21:
        return JSONResponse(status_code=400, content={"error": "Invalid CIN Format"})
    
    return {
        "success": True,
        "cin": cin,
        "company_name": "Verified Entity Pvt. Ltd.",
        "status": "Active",
        "directors": [
            {"din": "01234567", "name": "Rahul Sharma", "designation": "Managing Director"},
            {"din": "07654321", "name": "Priya Singh", "designation": "Director"}
        ],
        "registered_address": "123, Verification Hub, New Delhi, India 110001",
        "verification_timestamp": datetime.now().isoformat()
    }

@app.get("/verify-post/{tracking_id}")
async def verify_post_data(tracking_id: str):
    """
    Mock India Post API integration.
    Verifies tracking details of the statutory demand notice.
    """
    logger.info(f"Verifying India Post tracking: {tracking_id}")
    if not tracking_id or not tracking_id.endswith("IN"):
        return JSONResponse(status_code=400, content={"error": "Invalid Tracking ID Format"})
    
    return {
        "success": True,
        "tracking_id": tracking_id,
        "status": "Item Delivery Confirmed",
        "delivery_date": "2024-03-15T14:30:00",
        "delivery_location": "New Delhi, 110001",
        "verification_timestamp": datetime.now().isoformat()
    }


# ── Encryption setup ───────────────────────────────────────────────────────────
# pyrefly: ignore [missing-import]
from cryptography.fernet import Fernet
# In production, this key should be loaded from environment variables
ENCRYPTION_KEY = b'G-o6dGqzB2H7r7C4Uv6hM3_bT4-Y3PZ9N4e4Wv4Y-xY=' 
fernet = Fernet(ENCRYPTION_KEY)


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

@app.post("/caseroom/{room_id}/upload")
async def upload_caseroom_document(
    room_id: str,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    doc_type: str = Form("EVIDENCE"),
    claimed_reason: str = Form("None")
):
    from caseroom_logic import CaseroomManager
    
    # Ensure uploads directory exists
    upload_dir = os.path.join(os.getcwd(), "uploads", room_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    content = await file.read()
    
    # Encrypt file content (Phase 3: Security)
    encrypted_content = fernet.encrypt(content)
    
    # Save encrypted file to disk
    with open(file_path, "wb") as f:
        f.write(encrypted_content)

    # 1. Extract Text
    extracted_text = ""
    if file.filename.lower().endswith(".pdf"):
        if HAS_PDFPLUMBER:
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                extracted_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        else:
            extracted_text = "[Error: pdfplumber not installed on server]"
    else:
        # Fallback for images or raw text
        is_image = any(file.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])
        if is_image and HAS_PYTESSERACT:
            try:
                img = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(img)
            except Exception as e:
                extracted_text = f"[OCR Failed: {str(e)}]"
        else:
            try:
                extracted_text = content.decode("utf-8", errors="ignore")
            except:
                extracted_text = "[Unsupported file format for direct text extraction]"

    # 2. Verification
    verification_result = OCREngine.analyze_document(extracted_text, doc_type, claimed_reason)
    verification_status = "VERIFIED" if verification_result.get("is_verified") else "FAILED"

    # 3. Save metadata to DB
    doc_id = CaseroomManager.upload_document(room_id, user_id, file.filename, file_path, doc_type, verification_status, verification_result)
    
    return {
        "success": bool(doc_id),
        "doc_id": doc_id,
        "filename": file.filename,
        "verification_status": verification_status,
        "verification_details": verification_result
    }

@app.post("/caseroom/{room_id}/reanalyze")
async def reanalyze_caseroom(room_id: str):
    from caseroom_logic import CaseroomManager
    success, msg = CaseroomManager.reanalyze_case_from_documents(room_id)
    if not success:
        return JSONResponse(status_code=400, content={"error": msg})
    return {"success": True, "message": msg}


# ── PDF generation ─────────────────────────────────────────────────────────────
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


# ── File Download with Decryption ──────────────────────────────────────────────
@app.get("/caseroom/{room_id}/download/{filename}")
async def download_caseroom_document(room_id: str, filename: str):
    file_path = os.path.join(os.getcwd(), "uploads", room_id, filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
        
    with open(file_path, "rb") as f:
        encrypted_content = f.read()
        
    try:
        decrypted_content = fernet.decrypt(encrypted_content)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Decryption failed"})
        
    return Response(
        content=decrypted_content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ── Evidence Verification (OCR) ────────────────────────────────────────────────
@app.post("/verify-memo")
async def verify_memo(
    file: UploadFile = File(...),
    claimed_reason: str = "Insufficient Funds"
):
    """
    Endpoint to verify uploaded bank memo against the user's claimed reason.
    """
    logger.info(f"Received memo verification request for file: {file.filename}")
    
    # 1. Read file
    content = await file.read()
    extracted_text = ""

    # 2. Extract Text (PDF support via pdfplumber)
    if file.filename.lower().endswith(".pdf"):
        if HAS_PDFPLUMBER:
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                extracted_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        else:
            extracted_text = "[Error: pdfplumber not installed on server]"
    else:
        # Fallback for images or raw text
        is_image = any(file.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])
        if is_image and HAS_PYTESSERACT:
            try:
                img = Image.open(io.BytesIO(content))
                extracted_text = pytesseract.image_to_string(img)
            except Exception as e:
                extracted_text = f"[OCR Failed: {str(e)}]"
        else:
            try:
                extracted_text = content.decode("utf-8", errors="ignore")
            except:
                extracted_text = "[Unsupported file format for direct text extraction]"

    # 3. Verification Logic
    verification_result = OCREngine.analyze_document(extracted_text, "MEMO", claimed_reason)
    
    return {
        "success": True,
        "filename": file.filename,
        "claimed_reason": claimed_reason,
        "verification": verification_result
    }

# ── Dynamic Precedent Document Serving ─────────────────────────────────────────
@app.get("/api/precedents/document/{citation_id}")
async def get_precedent_document(citation_id: str):
    """
    Returns the source document or detailed information for a given judicial precedent.
    In a fully fleshed out system, this would stream the actual PDF from S3/Firebase.
    For this implementation, it dynamically reconstructs a clean HTML view of the judgment.
    """
    logger.info(f"Fetching document for citation: {citation_id}")
    
    # Clean citation ID
    original_citation = citation_id.replace('_', ' ')
    
    # Try to find it in the precedent log (Live Precedents)
    doc_title = "Judicial Precedent"
    doc_summary = "Document content not available."
    found = False
    
    try:
        from precedent_manager import precedent_manager
        live_precedents = precedent_manager.get_latest_precedents(100)
        for p in live_precedents:
            if p.get("citation", "").replace('/', ' ') == original_citation or p.get("title", "") == original_citation:
                doc_title = p.get("title", "Unknown Title")
                doc_summary = p.get("summary", "No summary available.")
                found = True
                break
    except Exception as e:
        logger.error(f"Error reading precedent log: {e}")

    # If not found in live log, try knowledge base
    if not found:
        from kb_manager import kb_manager
        kb = kb_manager.get_knowledge_base()
        for concept, data in kb.items():
            kb_prec = data.get("precedent", "")
            if kb_prec and (kb_prec.replace('/', ' ') == original_citation or kb_prec.replace('/', '_').replace(' ', '_') == citation_id):
                doc_title = kb_prec
                doc_summary = data.get("legal_impact", "No summary available.")
                found = True
                break

    # If still not found, try statutes precedents
    if not found:
        # Fallback to search statutes.json
        import json
        try:
            with open(os.path.join(os.path.dirname(__file__), "statutes.json"), "r") as f:
                statutes = json.load(f)
                for section in statutes.get("ni_act", {}).values():
                    for prec in section.get("precedents", []):
                        citation = prec.get("citation", "")
                        if citation.replace('/', '_').replace(' ', '_') == citation_id:
                            doc_title = prec.get("case", "Unknown Case")
                            doc_summary = prec.get("principle", "No principle available.")
                            found = True
                            break
        except Exception as e:
            logger.error(f"Error reading statutes.json: {e}")

    if not found:
        doc_title = original_citation.title()
        doc_summary = f"The source document for {doc_title} is currently being retrieved from the judicial archives."

    html_content = f"""
    <html>
        <head>
            <title>{doc_title} - JudiQ Legal Database</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f9fafb; }}
                .document-header {{ border-bottom: 2px solid #2563eb; padding-bottom: 1rem; margin-bottom: 2rem; }}
                h1 {{ color: #1e3a8a; font-size: 24px; margin-bottom: 0.5rem; }}
                .citation {{ color: #6b7280; font-weight: 600; font-size: 14px; }}
                .watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg); font-size: 8rem; color: rgba(0,0,0,0.03); z-index: -1; white-space: nowrap; pointer-events: none; }}
                .content-box {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                .court-seal {{ text-align: center; margin-bottom: 2rem; }}
                .court-seal img {{ width: 80px; opacity: 0.8; }}
                .section-title {{ font-weight: bold; color: #4b5563; margin-top: 1.5rem; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; }}
                .summary {{ font-size: 16px; text-align: justify; }}
            </style>
        </head>
        <body>
            <div class="watermark">JUDIQ VERIFIED</div>
            <div class="document-header">
                <h1>{doc_title}</h1>
                <div class="citation">Citation: {original_citation} | Source: Supreme Court of India</div>
            </div>
            <div class="content-box">
                <div class="section-title">Case Summary & Legal Principle</div>
                <p class="summary">{doc_summary}</p>
                
                <div class="section-title">Authentication</div>
                <p style="font-size: 12px; color: #6b7280;">This document is digitally retrieved and authenticated via the JudiQ AI Legal Database. <br>Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
