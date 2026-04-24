import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import uvicorn
from engine_core import JudiQEngine
from kb_manager import kb_manager
from pdf_generator import PDFGenerator
from database_manager import DatabaseManager
from normalizer import normalize_input
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JudiQ-API")
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="JudiQ Legal AI API v6", version="6.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/analyze")
async def analyze_options():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
        },
    )

@app.options("/{full_path:path}")
async def preflight(full_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )

@app.on_event("startup")
async def startup():
    DatabaseManager.init_db()
    logger.info("JudiQ Backend Started | Database Initialized")
@app.get("/")
async def health():
    return {"status": "operational", "version": "6.0.0"}
@app.post("/analyze")
async def analyze(request: Request):
    try:
        raw_data = await request.json()
        result = JudiQEngine.analyze_case(raw_data)
        normalized = normalize_input(raw_data)
        if normalized.get("user_id") and normalized.get("case_id") and normalized["user_id"] != "ANONYMOUS":
            DatabaseManager.save_case(normalized["user_id"], normalized["case_id"], normalized, result)
        return {
            "success": True,
            "score": result.get("score"),
            "verdict": result.get("verdict"),
            "risk_level": result.get("risk_level"),
            "analysis_confidence": result.get("analysis_confidence"),
            "decision": result.get("decision", {}),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "semantic_analysis": result.get("semantic_analysis", {}),
            "executive_summary": result.get("executive_summary", {}),
            "legal_analysis": result.get("legal_analysis", ""),
            "legal_strategy": result.get("legal_strategy", []),
            "reasoning_trace": result.get("reasoning_trace", []),
            "predicted_defences": result.get("defence_strategy", []),
            "draft": result.get("draft", ""),
            "draft_type": result.get("draft_type", "LEGAL_OPINION"),
            "timeline": result.get("timeline", []),
            "data": result
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/get-cases")
async def get_cases(user_id: str):
    cases = DatabaseManager.get_user_cases(user_id)
    return {"success": True, "count": len(cases), "cases": cases}

@app.get("/explain-score")
async def explain_score():
    return {
        "scoring_catalogue": kb_manager.get_scoring_catalogue(),
        "defence_weights": kb_manager.get_defence_legal_weights()
    }

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    """Generate PDF report with proper headers for download"""
    try:
        data = await request.json()
        
        # If no score in data, analyze the case first
        if "score" not in data:
            logger.info("Analyzing case before PDF generation")
            data = JudiQEngine.analyze_case(data)
        
        # Generate PDF
        pdf_bytes = PDFGenerator.generate_report(data)
        
        if not pdf_bytes or len(pdf_bytes) < 100:
            logger.error("PDF generation returned empty or invalid data")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to generate PDF"}
            )
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"JUDIQ_Report_{timestamp}.pdf"
        
        logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes, filename: {filename}")
        
        # Return with proper PDF headers
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation endpoint error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
