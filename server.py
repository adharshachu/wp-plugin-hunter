import asyncio
import os
import uuid
import time
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pipeline import Pipeline
from utils import GoogleSheetHandler, load_domains
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for jobs status
jobs: Dict[str, Dict] = {}

class JobStatus(BaseModel):
    job_id: str
    status: str
    processed: int
    total: int
    percentage: float
    results_count: int

async def run_pipeline_task(job_id: str, domains: List[str], tab_name: str):
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["total"] = len(domains)
    
    # Initialize Sheet Handler
    sheet_handler = None
    json_keyfile = os.getenv("GOOGLE_SHEETS_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    if json_keyfile and sheet_id:
        try:
            sheet_handler = GoogleSheetHandler(json_keyfile, sheet_id)
            sheet_handler.create_tab(tab_name)
        except Exception as e:
            print(f"Failed to initialize Google Sheets: {e}")

    pipeline = Pipeline(concurrency=50, sheet_handler=sheet_handler)
    
    async def progress_callback(processed, total):
        jobs[job_id]["processed"] = processed
        jobs[job_id]["results_count"] = len(pipeline.results)

    pipeline.set_progress_callback(progress_callback)
    
    try:
        await pipeline.run(domains)
        jobs[job_id]["status"] = "completed"
    except Exception as e:
        jobs[job_id]["status"] = f"error: {str(e)}"

@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    content = await file.read()
    
    # Save temp file
    temp_path = f"temp_{job_id}.txt"
    with open(temp_path, "wb") as f:
        f.write(content)
    
    domains = load_domains(temp_path)
    os.remove(temp_path)
    
    if not domains:
        return {"error": "No valid domains found in file"}

    # Dynamic tab name: Filename + Timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    clean_filename = "".join(x for x in file.filename if x.isalnum() or x in "._-")
    tab_name = f"{clean_filename}_{timestamp}"[:30] # Limit length

    jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "processed": 0,
        "total": len(domains),
        "results_count": 0,
        "tab_name": tab_name
    }

    background_tasks.add_task(run_pipeline_task, job_id, domains, tab_name)
    
    return {"job_id": job_id, "tab_name": tab_name}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    job = jobs[job_id]
    percentage = (job["processed"] / job["total"] * 100) if job["total"] > 0 else 0
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "processed": job["processed"],
        "total": job["total"],
        "percentage": round(percentage, 2),
        "results_count": job["results_count"],
        "tab_name": job.get("tab_name")
    }

# Serve Static Files (Built Frontend)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Fallback to index.html for SPA routing
        return FileResponse("frontend/dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
