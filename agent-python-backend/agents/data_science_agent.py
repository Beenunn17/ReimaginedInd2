import pandas as pd
import io
import base64
import re
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    from lightweight_mmm import preprocessing as _mmm_preprocessing
except Exception:
    _mmm_preprocessing = None

# -----------------------------
# Wrappers for MMM transforms
# -----------------------------
def _adstock(*args, **kwargs):
    if _mmm_preprocessing:
        func = getattr(_mmm_preprocessing, 'transform_adstock', None) or getattr(_mmm_preprocessing, 'apply_adstock', None)
        if func:
            try:
                return func(*args, **kwargs)
            except Exception:
                pass
    return args[0] if args else None

def _saturation(*args, **kwargs):
    if _mmm_preprocessing:
        func = getattr(_mmm_preprocessing, 'transform_saturation', None) or getattr(_mmm_preprocessing, 'apply_saturation', None)
        if func:
            try:
                return func(*args, **kwargs)
            except Exception:
                pass
    return args[0] if args else None

# -----------------------------
# MMM Training Function
# -----------------------------
def train_and_cache_mmm(df: pd.DataFrame, project_id: str, location: str, model_name: str) -> dict:
    """Train a Bayesian media mix model using lightweight_mmm and save outputs."""
    import pickle
    from datetime import datetime
    try:
        import numpy as np
        import jax.numpy as jnp
        import lightweight_mmm
        from lightweight_mmm import preprocessing, plot
    except Exception as exc:
        print(f"[ERROR] lightweight_mmm not available: {exc}")
        return {"error": f"lightweight_mmm unavailable: {exc}"}

    print(f"[MMM] Starting MMM training for dataset: {project_id}")
    try:
        # Detect target column
        target_col = next((col for cand in ["sales", "revenue", "y", "target"]
                           for col in df.columns if col.lower() == cand), None)
        if not target_col:
            numeric_cols = df.select_dtypes(include="number").columns
            if numeric_cols.empty:
                return {"error": "No numeric columns found for target."}
            target_col = numeric_cols[0]

        media_cols = [c for c in df.columns if c.lower().endswith("_spend") and c != target_col]
        if not media_cols:
            media_cols = [c for c in df.select_dtypes(include="number").columns if c != target_col]
        extra_cols = [c for c in df.select_dtypes(include="number").columns if c not in media_cols + [target_col]]

        media_data = df[media_cols].fillna(0).to_numpy(float)
        target = df[target_col].fillna(0).to_numpy(float)
        extra_features = df[extra_cols].fillna(0).to_numpy(float) if extra_cols else None

        media_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
        target_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
        media_data_scaled = media_scaler.fit_transform(media_data)
        target_scaled = target_scaler.fit_transform(target)
        extra_scaled = preprocessing.CustomScaler(divide_operation=jnp.mean).fit_transform(extra_features) if extra_cols else None
        costs = preprocessing.CustomScaler(divide_operation=jnp.mean).fit_transform(media_data)

        mmm = lightweight_mmm.LightweightMMM()
        mmm.fit(
            media=media_data_scaled,
            extra_features=extra_scaled,
            media_prior=costs,
            target=target_scaled,
            number_warmup=500,
            number_samples=500,
            number_chains=2,
        )

        dataset_name = os.path.splitext(os.path.basename(str(project_id or "dataset")))[0]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data_dir = os.getenv("DATA_DIR", "./data")
        model_dir = os.path.join(data_dir, "models", dataset_name, timestamp)
        os.makedirs(model_dir, exist_ok=True)

        with open(os.path.join(model_dir, "model.pkl"), "wb") as f:
            pickle.dump(mmm, f)

        media_effect_hat, roi_hat = mmm.get_posterior_metrics()
        diagnostics = {
            "media_cols": media_cols,
            "extra_cols": extra_cols,
            "target_col": target_col,
            "media_effect_hat": media_effect_hat.tolist(),
            "roi_hat": roi_hat.tolist(),
        }
        with open(os.path.join(model_dir, "diagnostics.json"), "w") as f:
            json.dump(diagnostics, f)

        plot_paths = {}
        fig = plot.plot_media_channel_posteriors(mmm, channel_names=media_cols)
        fig.savefig(os.path.join(model_dir, "posterior.png"))
        plot_paths["posterior"] = os.path.join(model_dir, "posterior.png")

        fig = plot.plot_response_curves(mmm, media_scaler, target_scaler)
        fig.savefig(os.path.join(model_dir, "response_curves.png"))
        plot_paths["response_curves"] = os.path.join(model_dir, "response_curves.png")

        fig = plot.plot_bars_media_metrics(metric=media_effect_hat, channel_names=media_cols)
        fig.savefig(os.path.join(model_dir, "media_effect.png"))
        plot_paths["media_effect"] = os.path.join(model_dir, "media_effect.png")

        fig = plot.plot_bars_media_metrics(metric=roi_hat, channel_names=media_cols)
        fig.savefig(os.path.join(model_dir, "roi.png"))
        plot_paths["roi"] = os.path.join(model_dir, "roi.png")

        rel_plot_paths = {k: os.path.relpath(v, data_dir) for k, v in plot_paths.items()}
        print(f"[MMM] Training complete. Model ID: {dataset_name}/{timestamp}")
        return {
            "model_id": f"{dataset_name}/{timestamp}",
            "plots": rel_plot_paths,
            "diagnostics": diagnostics,
        }
    except Exception as e:
        print(f"[MMM ERROR] {e}")
        return {"error": f"MMM training failed: {e}"}

# -----------------------------
# Agent Orchestration
# -----------------------------
def run_bayesian_mmm_agent(dataframe: pd.DataFrame, user_prompt: str, dataset_name: str,
                           project_id: str = "", location: str = "", model_name: str = "gemini-2.5-pro") -> dict:
    """Runs MMM first, then LLM summary."""
    print("[Agent] Running Bayesian MMM Agent...")
    train_result = train_and_cache_mmm(dataframe, project_id=dataset_name, location=location, model_name=model_name)
    if "error" in train_result:
        return train_result

    model_id = train_result["model_id"]
    plots = train_result.get("plots", {})
    diagnostics = train_result.get("diagnostics", {})

    try:
        vertexai.init(project=project_id, location=location)
        gen_model = GenerativeModel(model_name)
        metrics_str = ", ".join([
            f"{name}: effect={effect:.3f}, ROI={roi:.3f}"
            for name, effect, roi in zip(diagnostics.get("media_cols", []),
                                         diagnostics.get("media_effect_hat", []),
                                         diagnostics.get("roi_hat", []))
        ])
        summary_prompt = f"""
        You are a senior marketing analyst. The following channels have been fitted via a Bayesian media mix model:
        {', '.join(diagnostics.get("media_cols", []))}.
        Effectiveness & ROI metrics: {metrics_str}.
        User question: "{user_prompt}".
        Write a concise executive summary highlighting channel performance, diminishing returns, and a recommendation.
        """
        summary_text = gen_model.generate_content(summary_prompt).text.strip()
    except Exception as exc:
        summary_text = "MMM trained successfully. See plots for detailed insights."

    return {
        "model_id": model_id,
        "plots": plots,
        "diagnostics": diagnostics,
        "summary": summary_text,
    }
