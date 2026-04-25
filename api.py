import logging
import os
import shutil
import uvicorn  # type: ignore
from datetime import datetime
from fastapi import FastAPI, Request, Response, UploadFile, File  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

import importlib
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
    from database_manager import DatabaseManager
    try:
        DatabaseManager.init_db()
        logger.info("✅ JudiQ Backend Started | Database Initialized")
    except Exception as e:
        logger.error(f"⚠️  Database initialization failed: {e} — continuing without persistence.")


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/")
async def health():
    return {
        "status": "operational",
        "version": "7.0.0",
        "engine":  "JudiQ Legal AI v7 — Reasoning Architecture",
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
        normalized = normalize_input(raw_data)
        uid = normalized.get("user_id", "ANONYMOUS")
        cid = normalized.get("case_id", "")
        if uid and cid and uid != "ANONYMOUS":
            DatabaseManager.save_case(uid, cid, normalized, result)
    except Exception as e:
        logger.warning(f"[{request_id}] DB persistence failed (non-fatal): {e}")

    # ── Build response ─────────────────────────────────────────────────────────
    return {
        "success":             True,
        "request_id":          request_id,
        # Core scoring
        "score":               result.get("score"),
        "verdict":             result.get("verdict"),
        "risk_level":          result.get("risk_level"),
        "analysis_confidence": result.get("analysis_confidence"),
        # Decision panel
        "decision":            result.get("decision", {}),
        "strengths":           result.get("strengths", []),
        "weaknesses":          result.get("weaknesses", []),
        "issues":              result.get("issues", []),
        "legal_strategy":      result.get("legal_strategy", []),
        "alternative_evidence":result.get("alternative_evidence", []),
        # Semantic
        "semantic_analysis":   result.get("semantic_analysis", {}),
        "executive_summary":   result.get("executive_summary", {}),
        "legal_analysis":      result.get("legal_analysis", ""),
        "reasoning_trace":     result.get("reasoning_trace", []),
        # Defence & Draft
        "predicted_defences":  result.get("defence_strategy", []),
        "draft":               result.get("draft", ""),
        "draft_type":          result.get("draft_type", "LEGAL_OPINION"),
        "timeline":            result.get("timeline", []),
        # Reasoning Layer
        "case_summary":              result.get("case_summary", ""),
        "statutory_interpretation":  result.get("statutory_interpretation", []),
        "precedents":                result.get("precedents", []),
        "reasoning_trail":           result.get("reasoning_trail", []),
        # Decision-Support Layer
        "risks_and_rebuttals":       result.get("risks_and_rebuttals", []),
        "outcome_prediction":        result.get("outcome_prediction", {}),
        "translated_verdict":        result.get("translated_verdict", ""),
        "evidence_suggestions":      result.get("evidence_suggestions", []),
        # Full blob
        "data": result
    }


# ── Case history ───────────────────────────────────────────────────────────────
@app.get("/get-cases")
async def get_cases(user_id: str):
    try:
        cases = DatabaseManager.get_user_cases(user_id)
        return {"success": True, "count": len(cases), "cases": cases}
    except Exception as e:
        logger.error(f"get-cases failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ── Score explanation ──────────────────────────────────────────────────────────
@app.get("/explain-score")
async def explain_score():
    try:
        return {
            "scoring_catalogue": kb_manager.get_scoring_catalogue(),
            "defence_weights":   kb_manager.get_defence_legal_weights()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ── PDF generation ─────────────────────────────────────────────────────────────
@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    from pdf_generator import PDFGenerator
    from engine_core import JudiQEngine
    try:
        data = await request.json()
        if "score" not in data:
            data = JudiQEngine.analyze_case(data)

        pdf_bytes = PDFGenerator.generate_report(data)

        if not pdf_bytes or len(pdf_bytes) < 100:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": "PDF generation produced an empty file.",
                "user_message": "PDF could not be generated. Please try downloading as text instead."
            })

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"JUDIQ_Report_{timestamp}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type":        "application/pdf",
                "Content-Length":      str(len(pdf_bytes)),
                "Cache-Control":       "no-cache, no-store, must-revalidate",
            }
        )
    except ValidationError as ve:
        return JSONResponse(status_code=422, content={"success": False, "error": ve.message})
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "user_message": "PDF generation failed. Please use the text download option."
        })


# ── Document ingestion ─────────────────────────────────────────────────────────
@app.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    """
    Ingests a PDF or TXT file, extracts text, and returns it for AI analysis.
    Uses pdfplumber for robust PDF parsing.
    """
    try:
        if not file or not file.filename:
            return JSONResponse(status_code=400, content={"status": "error", "message": "No file uploaded"})

        filename = os.path.basename(file.filename)
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        
        if ext not in ["pdf", "txt"]:
            return JSONResponse(status_code=400, content={
                "status": "error", 
                "message": f"Unsupported file type: .{ext}. Please upload PDF or TXT."
            })

        # ── Size Check ──
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        content = await file.read()
        if len(content) > MAX_SIZE:
            return JSONResponse(status_code=413, content={
                "status": "error",
                "message": f"File too large ({len(content)//1024} KB). Maximum is 10 MB."
            })

        # ── Save temporarily ──
        import tempfile
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"judiq_{datetime.now().timestamp()}_{filename}")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        extracted_text = ""
        
        # ── PDF Extraction ──
        if ext == "pdf":
            if not HAS_PDFPLUMBER:
                extracted_text = "ERROR: pdfplumber is not installed on the server. Please contact support."
            else:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        pages = [page.extract_text() or "" for page in pdf.pages]
                    extracted_text = "\n".join(pages).strip()
                    
                    if not extracted_text:
                        extracted_text = "[PDF contained no extractable text — may be a scanned document or image-only PDF.]"
                except Exception as e:
                    extracted_text = f"ERROR: Failed to parse PDF: {str(e)}"
        
        # ── Text Extraction ──
        else:
            try:
                extracted_text = content.decode("utf-8", errors="replace").strip()
            except Exception as e:
                extracted_text = f"ERROR: Failed to read text file: {str(e)}"

        # ── Cleanup ──
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        # ── Response ──
        is_error = extracted_text.startswith("ERROR")
        return {
            "success": not is_error,
            "status": "success" if not is_error else "error",
            "filename": filename,
            "text": extracted_text,
            "length": len(extracted_text),
            "message": "Extraction complete" if not is_error else extracted_text
        }

    except Exception as e:
        logger.error(f"upload-doc error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={
            "status": "error",
            "success": False,
            "message": f"Server error during upload: {str(e)}"
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

