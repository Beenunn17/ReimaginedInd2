# ReimaginedInd Multi-Service Application

This repository contains a full‑stack application composed of a React frontend
(`agent-frontend`) and a Python backend (`agent-python-backend`) designed to
run efficiently both locally (via Docker Compose) and in production on
Google Cloud Run. The backend has been split into multiple services to
isolate heavy dependencies and improve cold‑start times.

## Overview of Services

| Service         | Purpose                                                        |
|-----------------|----------------------------------------------------------------|
| **api**         | Exposes all REST endpoints (data science agents, creative APIs, SEO and brand strategist agents) and enqueues Media Mix Modeling (MMM) jobs. |
| **mmm‑worker**  | Executes long‑running MMM training jobs asynchronously using RQ and Redis. |
| **seo‑browser** | Optional Playwright‑based worker for SEO scraping tasks. Presently a scaffold with no active tasks. |
| **redis**       | Provides a local Redis instance for job queuing. Use Memorystore in production. |
| **agent‑frontend** | Single‑page React application that interacts with the API. |

## Project Structure

```
repo-root/
  docker-compose.yml      # Compose file orchestrating all services
  agent-frontend/         # Vite + React frontend
  agent-python-backend/   # Backend code and Dockerfiles
    Dockerfile.api        # Lightweight API image
    Dockerfile.mmm        # Heavy MMM worker image
    requirements.api.txt  # Dependencies for the API
    requirements.mmm.txt  # Dependencies for MMM worker
    requirements.browser.txt # Playwright dependencies (also used in seo-browser)
    main.py               # FastAPI application with all endpoints
    agents/               # Business logic modules
    library/              # Image storage, image ops and models
    workers/              # RQ worker entrypoints
  seo-browser/            # Optional Playwright worker scaffold
    Dockerfile
    requirements.browser.txt
    workers/
  README.md               # This file
```

## Running Locally

Prerequisites:

* Docker and Docker Compose installed.
* Node.js installed if you want to run the frontend outside of Docker.

1. **Build and start the backend services**

   From the repository root run:

   ```sh
   docker compose build
   docker compose up
   ```

   This will start the following containers:

   * `api` listening on port **8000** (accessible at `http://localhost:8000`).
   * `mmm-worker` executing background MMM jobs.
   * `redis` for job queuing.
   * `seo-browser` (optional) running a Playwright worker with no tasks.

2. **Run the frontend**

   The React frontend is not containerised by default. To run it locally:

   ```sh
   cd agent-frontend
   npm install
   npm run dev
   ```

   The app will start at `http://localhost:5173` and proxy API requests to
   `http://localhost:8000` (configured in the Vite proxy settings).

3. **Dataset and model directories**

   The API expects CSV datasets to be placed in `/app/data` inside the
   container. During local development the `create_dummy_data.py` script can
   be run to generate sample data. When running via Docker Compose, this script
   is executed automatically at build time.

4. **Environment variables**

   The API is configured via a number of environment variables. When
   running locally via Docker Compose sensible defaults are provided. To
   run outside of Docker you must export these variables in your shell
   before starting the app:

   | Variable                     | Purpose                                                                                                   |
   |------------------------------|-----------------------------------------------------------------------------------------------------------|
   | `GOOGLE_CLOUD_PROJECT`       | GCP project ID used for Vertex AI. Leave empty to disable Vertex calls during local development.         |
   | `GOOGLE_APPLICATION_CREDENTIALS` | Path to your Google Application Default Credentials JSON file. Required when enabling Vertex or GCS. |
   | `VERTEX_LOCATION`            | Region for Vertex AI (e.g. `us-central1`).                                                               |
   | `REDIS_HOST`                 | Hostname of the Redis instance (`redis` in Compose or `localhost` when running locally).                 |
   | `REDIS_PORT`                 | Port of the Redis instance (6379).                                                                       |
   | `DATA_DIR`                   | Directory where CSV datasets and model artefacts are stored. Defaults to `./agent-python-backend/data`.  |
   | `IMAGE_LIBRARY_DIR`          | Directory used by the creative endpoints to store uploaded and generated images. Defaults to `./agent-python-backend/image_library`. |
   | `STORAGE_BACKEND`            | Selects the storage adapter (`local` or `gcs`). Local storage writes into `IMAGE_LIBRARY_DIR`.           |
   | `GCS_BUCKET`                 | Name of the GCS bucket to use when `STORAGE_BACKEND=gcs`.                                                |

   When running the API without Docker you can start it using uvicorn:

   ```bash
   # Create and activate a virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies (API only)
   pip install -r agent-python-backend/requirements.api.txt
   
   # (Optional) Install MMM worker deps if you plan to train models
   pip install -r agent-python-backend/requirements.mmm.txt
   
   # Export environment variables for data and image storage
   export DATA_DIR=$(pwd)/agent-python-backend/data
   export IMAGE_LIBRARY_DIR=$(pwd)/agent-python-backend/image_library
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   
   # Start a local Redis if not already running
   docker run --rm -p 6379:6379 redis:7-alpine &
   
   # Launch the API using uvicorn with uvloop and httptools
   uvicorn main:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools
   ```

## Deploying to Google Cloud Run

In production each service should be deployed as a separate Cloud Run service
and connected to a Cloud Memorystore instance for Redis. Use Workload
Identity to authenticate with GCS and other Google Cloud APIs instead of
mounting service account keys.

1. **Build container images**

   ```sh
   gcloud builds submit --tag gcr.io/$PROJECT_ID/reimaginedind-api ./agent-python-backend \
     --project=$PROJECT_ID --substitutions=_DOCKERFILE=Dockerfile.api

   gcloud builds submit --tag gcr.io/$PROJECT_ID/reimaginedind-mmm ./agent-python-backend \
     --project=$PROJECT_ID --substitutions=_DOCKERFILE=Dockerfile.mmm

   # Optional: build the SEO browser worker
   gcloud builds submit --tag gcr.io/$PROJECT_ID/reimaginedind-seo ./seo-browser \
     --project=$PROJECT_ID
   ```

2. **Provision Redis (Memorystore)**

   Create a Memorystore instance and note its IP address and port. Configure
   `REDIS_HOST` and `REDIS_PORT` environment variables on your Cloud Run
   services to point to this instance.

3. **Deploy services**

   ```sh
   gcloud run deploy reimaginedind-api \
     --image gcr.io/$PROJECT_ID/reimaginedind-api \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars REDIS_HOST=<memorystore-ip>,REDIS_PORT=<port>,DATA_DIR=/data,STORAGE_BACKEND=gcs,GCS_BUCKET=<your-bucket> \
     --service-account <your-workload-identity-service-account>

   gcloud run deploy reimaginedind-mmm \
     --image gcr.io/$PROJECT_ID/reimaginedind-mmm \
     --region us-central1 \
     --no-allow-unauthenticated \
     --set-env-vars REDIS_HOST=<memorystore-ip>,REDIS_PORT=<port>,DATA_DIR=/data,STORAGE_BACKEND=gcs,GCS_BUCKET=<your-bucket> \
     --service-account <your-workload-identity-service-account>

   # Deploy the SEO browser worker if needed
   gcloud run deploy reimaginedind-seo \
     --image gcr.io/$PROJECT_ID/reimaginedind-seo \
     --region us-central1 \
     --no-allow-unauthenticated \
     --set-env-vars REDIS_HOST=<memorystore-ip>,REDIS_PORT=<port> \
     --service-account <your-workload-identity-service-account>
   ```

4. **GCS storage**

   When `STORAGE_BACKEND=gcs` the backend writes image assets to your
   designated GCS bucket. The current implementation of `library.storage`
   contains TODOs for integrating the `google-cloud-storage` client. You
   should install `google-cloud-storage`, implement the upload and signed URL
   logic, and grant the Cloud Run service account access to the bucket.

## Notes and TODOs

* The MMM training functions now use the [lightweight_mmm](https://github.com/google/lightweight_mmm)
  library to fit a Bayesian media mix model. Model artefacts (pickled
  model, diagnostics JSON and plots) are saved under
  ``$DATA_DIR/models/<dataset>/<timestamp>/`` and can be listed via the
  ``GET /mmm/plots`` endpoint. You can adjust priors and sampling
  parameters in ``agents/data_science_agent.py``.
* Basic image editing operations (grayscale, invert and brightness) are
  implemented in the `/library/images/edit` endpoint. Additional filters
  and adjustments can be added by extending `library/image_ops.py` and
  updating the endpoint accordingly.
* The SEO browser worker is a scaffold. Add RQ job handling and Playwright
  tasks to `seo-browser/workers/seo_worker.py` when ready.
* Ensure that any calls to external services (e.g. Vertex AI, OpenAI) are
  properly authenticated. If credentials are unavailable in your environment,
  mock those calls and leave clear TODO notes for future development.