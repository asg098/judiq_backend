import logging
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

app = FastAPI(title="JudiQ Legal AI API v6", version="6.0.0")

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
        if normalized.get("user_id") and normalized.get("case_id"):
            DatabaseManager.save_case(normalized["user_id"], normalized["case_id"], normalized, result)
        return {
            "success": True, 
            "score": result.get("score"),
            "verdict": result.get("verdict"),
            "risk_level": result.get("risk_level"),
            "executive_summary": result.get("executive_summary"),
            "legal_analysis": result.get("legal_analysis"),
            "predicted_defences": result.get("defence_strategy"),
            "draft": result.get("draft"),
            "timeline": result.get("timeline"),
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
    data = await request.json()
    if "score" not in data:
        data = JudiQEngine.analyze_case(data)
    pdf_bytes = PDFGenerator.generate_report(data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=JudiQ_Report.pdf"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
