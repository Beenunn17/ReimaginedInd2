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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

# Mount the data directory to serve model artifacts and other static data. This
# allows clients to fetch plot images saved under DATA_DIR via URLs like
# /data/models/<dataset>/<timestamp>/<plot>.png. Without this mount the
# images would not be reachable from the frontend.
if os.path.isdir(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Mount the image library directory if it exists.  The creative asset
# endpoints write files into IMAGE_LIBRARY_DIR via library.storage.save_bytes().
# By exposing the directory under `/image_library` here, the frontend can
# request thumbnails and originals directly.  When served locally the
# resulting URLs look like `/image_library/orig/<uid>.jpg` or `/image_library/t/<uid>.jpg`.
IMAGE_LIBRARY_DIR = os.getenv("IMAGE_LIBRARY_DIR", "./image_library")
if os.path.isdir(IMAGE_LIBRARY_DIR):
    app.mount("/image_library", StaticFiles(directory=IMAGE_LIBRARY_DIR), name="image_library")

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
async def analyze_data(
    dataset_filename: str = Form(...),
    prompt: str = Form(...),
    model_type: str = Form("standard"),
    revenue_target: Optional[float] = Form(None),
):
    """Analyze a dataset using either a standard or Bayesian MMM flow.

    The ``model_type`` form field selects which analysis to run. When
    ``model_type`` equals ``bayesian`` the advanced MMM training using
    lightweight_mmm is invoked before generating a summary. Otherwise the
    standard LLM‑only analysis is performed.
    """
    filepath = os.path.join(DATA_DIR, dataset_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_filename} not found.")
    df = pd.read_csv(filepath)
    # Branch based on model_type
    if model_type.lower() == "bayesian":
        # For Bayesian flow, call the MMM agent. Pass dataset_filename as dataset_name for artifact naming.
        result = run_bayesian_mmm_agent(
            dataframe=df,
            user_prompt=prompt,
            dataset_name=dataset_filename,
            project_id=PROJECT_ID,
            location=LOCATION,
            model_name=MODEL_NAME,
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    # Default: standard analysis
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

@app.get("/mmm/plots")
async def get_mmm_plots(model_id: str):
    """Return the list of plot file URLs for a given MMM model.

    The ``model_id`` must be in the form ``<dataset>/<timestamp>`` and
    resolves to a directory under ``DATA_DIR/models``. The endpoint
    inspects this directory for any PNG files and returns their names
    and URLs. If the directory does not exist or contains no images an
    HTTP 404 is returned.
    """
    # Validate and normalise model_id
    if not model_id or "/" not in model_id:
        raise HTTPException(status_code=400, detail="model_id must be in the form <dataset>/<timestamp>")
    # Build the model directory path
    model_dir = os.path.join(DATA_DIR, "models", *model_id.split("/"))
    if not os.path.isdir(model_dir):
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found.")
    # Scan for image files (png)
    plot_files = [f for f in os.listdir(model_dir) if f.lower().endswith(".png")]
    if not plot_files:
        raise HTTPException(status_code=404, detail=f"No plots found for model {model_id}.")
    # Build URLs relative to the mounted /data static route
    results = []
    for fname in sorted(plot_files):
        rel_path = os.path.relpath(os.path.join(model_dir, fname), DATA_DIR)
        results.append({"name": fname, "url": f"/data/{rel_path}".replace("\\", "/")})
    return {"model_id": model_id, "plots": results}

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
    """Apply a simple image filter to an uploaded or data URL image.

    Supported operations include:

    - ``grayscale``: Convert the image to grayscale.
    - ``invert``: Invert the colours of the image.
    - ``brightness``: Apply a brightness enhancement (increase by 20%).

    If an unsupported operation is requested a 400 error is returned. The
    resulting image is saved back into the image library and the URL
    returned. The original image is not overwritten.
    """
    if not save_bytes or not image_ops:
        raise HTTPException(status_code=500, detail="Image library not configured.")
    raw_data = await file.read() if file else (
        base64.b64decode(data_url.split(",", 1)[1]) if data_url else None
    )
    if not raw_data:
        raise HTTPException(status_code=400, detail="No image data provided.")
    # Open the image using Pillow via image_ops helper
    from PIL import Image, ImageEnhance, ImageOps  # type: ignore
    img = Image.open(io.BytesIO(raw_data)).convert("RGB")
    if operation == "grayscale":
        img = ImageOps.grayscale(img).convert("RGB")
    elif operation == "invert":
        img = ImageOps.invert(img)
    elif operation == "brightness":
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.2)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported edit operation '{operation}'.")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    uid = str(uuid.uuid4())
    return {"orig": save_bytes(f"orig/{uid}.jpg", buffer.getvalue())}

@app.get("/library/assets")
async def list_library_assets():
    """List all assets stored in the image library in reverse chronological order.

    The image library saves files into subdirectories named ``orig``, ``m``
    (medium) and ``t`` (thumbnail). This endpoint enumerates the original
    images and returns a list of asset objects each containing the
    original, medium and thumbnail URLs. Assets are ordered by file
    modification time so that the most recently saved images appear first.
    """
    if not os.path.isdir(IMAGE_LIBRARY_DIR):
        raise HTTPException(status_code=404, detail="Image library not found.")
    orig_dir = os.path.join(IMAGE_LIBRARY_DIR, "orig")
    if not os.path.isdir(orig_dir):
        return {"assets": []}
    assets = []
    # Iterate over files in the orig directory
    for fname in os.listdir(orig_dir):
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        uid, _ = os.path.splitext(fname)
        # Determine modification time for ordering
        fpath = os.path.join(orig_dir, fname)
        try:
            mtime = os.path.getmtime(fpath)
        except Exception:
            mtime = 0
        asset = {
            "id": uid,
            "orig": f"/image_library/orig/{fname}",
            "medium": f"/image_library/m/{uid}.jpg",
            "thumb": f"/image_library/t/{uid}.jpg",
            "mtime": mtime,
        }
        assets.append(asset)
    # Sort by modification time descending
    assets.sort(key=lambda x: x["mtime"], reverse=True)
    # Drop mtime from response
    for asset in assets:
        asset.pop("mtime", None)
    return {"assets": assets}

@app.post("/library/animate")
async def animate_endpoint(request: Request):
    try:
        from library.veo3 import generate_animation
    except ImportError:
        raise HTTPException(status_code=501, detail="Animation generation not available.")
    params = await request.json()
    return generate_animation(**params)
