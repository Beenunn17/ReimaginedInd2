print("🔥 Starting main.py")

import os
import sys
import uuid
import base64
import json
import asyncio
import pandas as pd
import httpx
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, WebSocket, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import vertexai

# --- Environment & Config ---
GOOGLE_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

PROJECT_ID = GOOGLE_PROJECT or "braidai"
LOCATION = VERTEX_LOCATION
MODEL_NAME = "gemini-2.5-pro"

# --- Vertex Init ---
if GOOGLE_PROJECT:
    try:
        vertexai.init(project=GOOGLE_PROJECT, location=VERTEX_LOCATION)
        print(f"[startup] Vertex AI initialized for project {GOOGLE_PROJECT} in {VERTEX_LOCATION}")
    except Exception as e:
        print(f"[startup] Vertex init skipped: {e}", file=sys.stderr)
else:
    print("[startup] GOOGLE_CLOUD_PROJECT not set; Vertex disabled.")

# --- Optional Dependencies ---
try:
    from redis import Redis
    from rq import Queue, Job
except ImportError:
    Redis = None
    Queue = None
    Job = None

try:
    from library.storage import save_bytes, signed_url
    from library import image_ops
except ImportError:
    save_bytes = None
    signed_url = None
    image_ops = None

# --- Agent Imports ---
from agents.data_science_agent import run_standard_agent, run_follow_up_agent
from agents.seo_agent import find_sitemap, generate_prompts_for_url, run_full_seo_analysis
from agents.creative_agent import generate_ad_creative
from agents import brand_strategist_agent, creative_director_agent, copywriter_agent

# --- Redis Init ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

if Redis and Queue:
    try:
        redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        mmm_queue = Queue("mmm", connection=redis_conn)
    except Exception as e:
        print(f"[startup] Redis init failed: {e}")
        redis_conn = None
        mmm_queue = None
else:
    redis_conn = None
    mmm_queue = None

# --- App Init ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware ---
@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/image_library/"):
        response.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return response

# --- SEO Endpoints ---
@app.post("/validate-sitemaps")
async def validate_sitemaps_endpoint(urls: list = Form(...)):
    results = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [find_sitemap(url, client) for url in urls]
        sitemap_locations = await asyncio.gather(*tasks)
        for url, sitemap_loc in zip(urls, sitemap_locations):
            results.append({
                "url": url,
                "status": "found" if sitemap_loc else "not_found",
                "sitemap_url": sitemap_loc
            })
    return {"results": results}

@app.post("/generate-prompts")
async def get_generated_prompts(url: str = Form(...), competitors: str = Form("")):
    categorized_prompts = generate_prompts_for_url(url, competitors, PROJECT_ID, LOCATION)
    if 'error' in categorized_prompts:
        raise HTTPException(status_code=500, detail=categorized_prompts['error'])
    return {"prompts": categorized_prompts}

@app.websocket("/ws/seo-analysis")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        your_site = data.get("yourSite")
        competitors = data.get("competitors", [])
        prompts = data.get("prompts")
        if not your_site or not prompts:
            await websocket.send_json({"status": "error", "message": "Missing site URL or prompts."})
            return
        final_report = await run_full_seo_analysis(websocket, PROJECT_ID, LOCATION, your_site, competitors, prompts)
        await websocket.send_json({"status": "complete", "report": final_report})
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        await websocket.close()

# --- Creative Endpoint ---
@app.post("/generate-creative")
async def generate_creative_endpoint(
    platform: str = Form(...),
    customSubject: str = Form(...),
    sceneDescription: str = Form(...),
    imageType: str = Form(...),
    style: str = Form(...),
    camera: str = Form(...),
    lighting: str = Form(...),
    composition: str = Form(...),
    modifiers: str = Form(...),
    negativePrompt: str = Form(...),
    subjectImage: Optional[str] = Form(None),
    sceneImage: Optional[str] = Form(None)
):
    prompt_components = {
        "customSubject": customSubject,
        "sceneDescription": sceneDescription,
        "imageType": imageType,
        "style": style,
        "camera": camera,
        "lighting": lighting,
        "composition": composition,
        "modifiers": modifiers,
        "negativePrompt": negativePrompt
    }
    asset_data = generate_ad_creative(
        project_id=PROJECT_ID,
        location=LOCATION,
        platform=platform,
        prompt_components=prompt_components,
        subject_image_b64=subjectImage,
        scene_image_b64=sceneImage
    )
    if asset_data:
        return asset_data
    raise HTTPException(status_code=500, detail="Failed to generate creative.")

# --- Data Science Endpoints ---
@app.get("/preview/{dataset_filename}")
async def get_data_preview(dataset_filename: str):
    filepath = os.path.join(DATA_DIR, dataset_filename)
    df = pd.read_csv(filepath).round(2)
    return json.loads(df.head().to_json(orient='split'))

@app.post("/analyze")
async def analyze_data(dataset_filename: str = Form(...), prompt: str = Form(...)):
    filepath = os.path.join(DATA_DIR, dataset_filename)
    df = pd.read_csv(filepath)
    return run_standard_agent(df, prompt, PROJECT_ID, LOCATION, MODEL_NAME)

@app.post("/follow-up")
async def follow_up_analysis(
    dataset_filename: str = Form(...),
    original_prompt: str = Form(...),
    follow_up_history: str = Form(...),
    follow_up_prompt: str = Form(...)
):
    filepath = os.path.join(DATA_DIR, dataset_filename)
    df = pd.read_csv(filepath)
    history_list = json.loads(follow_up_history)
    history_str = "".join(
        f"{'User' if t.get('sender') == 'user' else 'Agent'}: {t.get('text' if t.get('sender') == 'user' else 'summary')}\n"
        for t in history_list
    )
    return run_follow_up_agent(df, original_prompt, history_str, follow_up_prompt, PROJECT_ID, LOCATION, MODEL_NAME)

# --- Brand Strategy & Creative Director ---
@app.post("/analyze-brand")
async def analyze_brand_endpoint(request: Request):
    form_data = await request.form()
    brand_name = form_data.get("brandName")
    website_url = form_data.get("websiteUrl")
    ad_library_url = form_data.get("adLibraryUrl")
    user_brief = form_data.get("userBrief")
    if not brand_name or not website_url or not user_brief:
        raise HTTPException(status_code=400, detail="Missing required fields.")
    analysis_data = await brand_strategist_agent.analyze_brand_with_llm(
        project_id=PROJECT_ID,
        location=LOCATION,
        brand_name=brand_name,
        website_url=website_url,
        ad_library_url=ad_library_url,
        user_brief=user_brief
    )
    if analysis_data.get("error"):
        raise HTTPException(status_code=500, detail=analysis_data["error"])
    return JSONResponse(content=analysis_data)

@app.post("/generate-assets-from-brief")
async def generate_assets_endpoint(request: Request):
    data = await request.json()
    brand_name = data.get("brandName")
    website_url = data.get("websiteUrl")
    ad_library_url = data.get("adLibraryUrl")
    user_brief = data.get("userBrief")
    selected_strategy = data.get("selectedStrategy")
    if not all([brand_name, website_url, user_brief, selected_strategy]):
        raise HTTPException(status_code=400, detail="Missing required data.")
    asset_results = await creative_director_agent.brief_to_prompts_and_assets(
        project_id=PROJECT_ID,
        location=LOCATION,
        brand_name=brand_name,
        website_url=website_url,
        ad_library_url=ad_library_url,
        user_brief=user_brief,
        selected_strategy=selected_strategy
    )
    return JSONResponse(content=asset_results)

@app.post("/generate-social-copy")
async def generate_social_copy_endpoint(request: Request):
    data = await request.json()
    brand_name = data.get("brandName")
    user_brief = data.get("userBrief")
    selected_strategy = data.get("selectedStrategy")
    if not all([brand_name, user_brief, selected_strategy]):
        raise HTTPException(status_code=400, detail="Missing required data.")
    copy_results = copywriter_agent.generate_social_posts(
        project_id=PROJECT_ID,
        location=LOCATION,
        brand_name=brand_name,
        user_brief=user_brief,
        selected_strategy=selected_strategy
    )
    return JSONResponse(content=copy_results)

# --- MMM Endpoints ---
@app.post("/mmm/train")
async def mmm_train_endpoint(
    dataset_filename: str = Form(...),
    project_id: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
):
    if mmm_queue is None:
        raise HTTPException(status_code=500, detail="Job queue not configured.")
    from agents.data_science_agent import train_and_cache_mmm_job
    job = mmm_queue.enqueue(
        train_and_cache_mmm_job,
        kwargs={
            "dataset_filename": dataset_filename,
            "project_id": project_id or PROJECT_ID,
            "location": location or LOCATION,
            "model_name": model_name or MODEL_NAME,
        },
    )
    return {"job_id": job.id, "status": job.get_status(refresh=False)}

@app.get("/jobs/{job_id}")
async def job_status_endpoint(job_id: str):
    if not all([mmm_queue, redis_conn, Job]):
        raise HTTPException(status_code=500, detail="Job queue not configured.")
    job = Job.fetch(job_id, connection=redis_conn)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job.get_status(refresh=False),
        "result": job.result if job.is_finished else None,
        "error": str(job.exc_info) if job.is_failed else None,
    }

# --- Creative Library ---
@app.post("/library/images/save")
async def save_image_endpoint(
    data_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    if not save_bytes or not image_ops:
        raise HTTPException(status_code=500, detail="Image library not configured.")
    raw_data = await file.read() if file else (
        base64.b64decode(data_url.split(",", 1)[1]) if data_url else None
    )
    if not raw_data:
        raise HTTPException(status_code=400, detail="No image data provided.")
    uid = str(uuid.uuid4())
    medium_bytes = image_ops.resize_image(raw_data, 1024)
    thumb_bytes = image_ops.resize_image(raw_data, 256)
    return {
        "orig": save_bytes(f"orig/{uid}.jpg", raw_data),
        "medium": save_bytes(f"m/{uid}.jpg", medium_bytes),
        "thumb": save_bytes(f"t/{uid}.jpg", thumb_bytes),
    }

@app.post("/library/images/text-overlay")
async def text_overlay_endpoint(
    text: str = Form(...),
    data_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    if not save_bytes or not image_ops:
        raise HTTPException(status_code=500, detail="Image library not configured.")
    raw_data = await file.read() if file else (
        base64.b64decode(data_url.split(",", 1)[1]) if data_url else None
    )
    if not raw_data:
        raise HTTPException(status_code=400, detail="No image data provided.")
    modified_bytes = image_ops.overlay_text(raw_data, text)
    uid = str(uuid.uuid4())
    return {"orig": save_bytes(f"orig/{uid}.jpg", modified_bytes)}

@app.post("/library/images/edit")
async def edit_image_endpoint(
    operation: str = Form(...),
    data_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    raise HTTPException(status_code=501, detail="Image editing not implemented.")

@app.post("/library/animate")
async def animate_endpoint(request: Request):
    try:
        from library.veo3 import generate_animation
    except ImportError:
        raise HTTPException(status_code=501, detail="Animation generation not available.")
    params = await request.json()
    return generate_animation(**params)
