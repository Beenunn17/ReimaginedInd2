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

# -----------------------------------------------------------------------------
# MMM compatibility wrappers and training stubs
#
# To insulate the data science agent from API changes in lightweight_mmm,
# we define wrappers that attempt to use both the old `transform_*` and new
# `apply_*` function names. If the library is unavailable or the call fails,
# these wrappers fall back to returning the input unmodified. We also provide
# a simple stubbed implementation of a media mix modeling (MMM) training
# routine. In production this would invoke a heavy dependency such as JAX
# or NumPyro, but here we simulate a result so that job handling and API
# integration can be exercised without the full stack.
try:
    from lightweight_mmm import preprocessing as _mmm_preprocessing  # type: ignore[attr-defined]
except Exception:
    _mmm_preprocessing = None


def _adstock(*args, **kwargs):
    """Wrapper for adstock transformation compatible with multiple API versions.

    Attempts to call `transform_adstock` (older API) or `apply_adstock` (newer
    API) on the lightweight_mmm preprocessing module. If neither is available
    or the call fails, returns the first positional argument unchanged.
    """
    if _mmm_preprocessing:
        func = None
        # Attempt to find the appropriate function name
        if hasattr(_mmm_preprocessing, 'transform_adstock'):
            func = getattr(_mmm_preprocessing, 'transform_adstock')
        elif hasattr(_mmm_preprocessing, 'apply_adstock'):
            func = getattr(_mmm_preprocessing, 'apply_adstock')
        if func:
            try:
                return func(*args, **kwargs)
            except Exception:
                pass
    # Safe fallback: return the input as-is
    return args[0] if args else None


def _saturation(*args, **kwargs):
    """Wrapper for saturation transformation compatible with multiple API versions.

    Attempts to call `transform_saturation` or `apply_saturation`; falls back
    to returning the first positional argument unchanged on error.
    """
    if _mmm_preprocessing:
        func = None
        if hasattr(_mmm_preprocessing, 'transform_saturation'):
            func = getattr(_mmm_preprocessing, 'transform_saturation')
        elif hasattr(_mmm_preprocessing, 'apply_saturation'):
            func = getattr(_mmm_preprocessing, 'apply_saturation')
        if func:
            try:
                return func(*args, **kwargs)
            except Exception:
                pass
    return args[0] if args else None


def train_and_cache_mmm(df: pd.DataFrame, project_id: str, location: str, model_name: str) -> dict:
    """Train a full Bayesian media mix model using lightweight_mmm.

    This function wraps the data preparation, scaling, model fitting and
    artifact persistence into a single call. It identifies the target
    column and media spend columns from the provided DataFrame, applies
    appropriate scalers, fits a Bayesian MMM with Google's
    ``lightweight_mmm`` library and writes out the resulting model,
    diagnostics and plots to a timestamped directory under the
    configured ``DATA_DIR``.

    The heavy lifting (NumPyro/JAX sampling) is encapsulated here so
    that callers simply receive a dictionary containing the model ID
    (used for later retrieval), the relative plot paths and any
    diagnostics. If the underlying libraries are unavailable or an
    unexpected error occurs the returned dict will contain an
    ``error`` key instead.

    Args:
        df: The DataFrame containing the MMM data. Should include a
            revenue/sales target column and one or more spend columns.
        project_id: Unused but kept for API compatibility.
        location: Unused but kept for API compatibility.
        model_name: Unused but kept for API compatibility.

    Returns:
        A dictionary with a ``model_id`` string, a ``plots`` mapping of
        descriptive plot names to relative file paths, a ``diagnostics``
        object, and optionally an ``error`` field if training fails.
    """
    import os
    import json
    import pickle
    from datetime import datetime
    # Defer heavy imports until needed to keep startup time low
    try:
        import numpy as np  # noqa: F401
        import jax.numpy as jnp  # type: ignore
        import lightweight_mmm
        from lightweight_mmm import preprocessing, plot
    except Exception as exc:
        return {"error": f"lightweight_mmm unavailable: {exc}"}

    try:
        # Identify the target (response) column. Prefer common names if present.
        target_col = None
        for cand in ["sales", "revenue", "y", "target"]:
            for col in df.columns:
                if col.lower() == cand:
                    target_col = col
                    break
            if target_col:
                break
        # Fallback: use the first numeric column as target
        if not target_col:
            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) == 0:
                return {"error": "No numeric columns found for target."}
            target_col = numeric_cols[0]

        # Media spend columns: those ending in _spend (case insensitive)
        media_cols = [
            c for c in df.columns
            if c.lower().endswith("_spend") and c != target_col
        ]
        if not media_cols:
            # If no spend columns match the pattern, treat all numeric cols except target as media
            media_cols = [c for c in df.select_dtypes(include="number").columns if c != target_col]
        # Extra features: other numeric columns not in media or target
        extra_cols = [
            c for c in df.select_dtypes(include="number").columns
            if c not in media_cols + [target_col]
        ]

        # Prepare numpy arrays. Fill NaNs to zeros to avoid sampler failures.
        media_data = df[media_cols].fillna(0.0).to_numpy(dtype=float)
        target = df[target_col].fillna(0.0).to_numpy(dtype=float)
        extra_features = (
            df[extra_cols].fillna(0.0).to_numpy(dtype=float) if extra_cols else None
        )

        # Scale media and target. We divide by the mean to bring values to O(1).
        media_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
        target_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
        media_data_scaled = media_scaler.fit_transform(media_data)
        target_scaled = target_scaler.fit_transform(target)

        extra_scaled = None
        if extra_cols:
            extra_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
            extra_scaled = extra_scaler.fit_transform(extra_features)
        # Costs are scaled spend values; scaling helps the prior reflect channel magnitude
        cost_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
        costs = cost_scaler.fit_transform(media_data)

        # Fit the Bayesian MMM. Use modest chain/sample counts to keep compute reasonable.
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

        # Prepare directory for saving artifacts
        # Determine dataset name from project_id or fallback constant
        dataset_name = os.path.splitext(os.path.basename(str(project_id or "dataset")))[0]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        data_dir = os.getenv("DATA_DIR", "./data")
        model_dir = os.path.join(data_dir, "models", dataset_name, timestamp)
        os.makedirs(model_dir, exist_ok=True)

        # Save the fitted model
        model_path = os.path.join(model_dir, "model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(mmm, f)

        # Compute posterior metrics for diagnostics and ROI
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

        # Generate plots. Each plotting function returns a matplotlib Figure.
        plot_paths = {}
        # Posterior distributions per channel
        fig = plot.plot_media_channel_posteriors(media_mix_model=mmm, channel_names=media_cols)
        posterior_path = os.path.join(model_dir, "posterior.png")
        fig.savefig(posterior_path)
        plot_paths["posterior"] = posterior_path
        # Response curves
        fig = plot.plot_response_curves(
            media_mix_model=mmm,
            media_scaler=media_scaler,
            target_scaler=target_scaler,
        )
        response_path = os.path.join(model_dir, "response_curves.png")
        fig.savefig(response_path)
        plot_paths["response_curves"] = response_path
        # Media effect bars
        fig = plot.plot_bars_media_metrics(metric=media_effect_hat, channel_names=media_cols)
        effect_path = os.path.join(model_dir, "media_effect.png")
        fig.savefig(effect_path)
        plot_paths["media_effect"] = effect_path
        # ROI bars
        fig = plot.plot_bars_media_metrics(metric=roi_hat, channel_names=media_cols)
        roi_path = os.path.join(model_dir, "roi.png")
        fig.savefig(roi_path)
        plot_paths["roi"] = roi_path

        # Return relative paths (from DATA_DIR) so that callers can construct URLs
        rel_plot_paths = {k: os.path.relpath(v, data_dir) for k, v in plot_paths.items()}
        return {
            "model_id": f"{dataset_name}/{timestamp}",
            "plots": rel_plot_paths,
            "diagnostics": diagnostics,
        }
    except Exception as e:
        return {"error": f"MMM training failed: {str(e)}"}


def train_and_cache_mmm_job(dataset_filename: str, project_id: str, location: str, model_name: str) -> dict:
    """Wrapper to load a dataset from disk and invoke the MMM training.

    This function is designed to be enqueued as a background job via RQ. It
    resolves the DATA_DIR from the environment, reads the specified CSV file
    into a DataFrame and delegates to `train_and_cache_mmm` for the actual
    model fitting.
    """
    data_dir = os.getenv("DATA_DIR", "./data")
    filepath = os.path.join(data_dir, dataset_filename)
    df = pd.read_csv(filepath)
    return train_and_cache_mmm(df, project_id, location, model_name)

def get_df_schema(df: pd.DataFrame) -> str:
    return pd.io.json.build_table_schema(df)

def run_standard_agent(dataframe: pd.DataFrame, user_prompt: str, project_id: str, location: str, model_name: str) -> dict:
    vertexai.init(project=project_id, location=location)
    generative_model = GenerativeModel(model_name)
    
    df_schema = get_df_schema(dataframe)
    visualization_instruction = ""
    plot_keywords = ['plot', 'chart', 'graph', 'visualize', 'bar', 'line', 'scatter', 'hist']
    if any(keyword in user_prompt.lower() for keyword in plot_keywords):
        visualization_instruction = "The user has specifically requested a visualization, so you MUST provide relevant Python code for the 'visualizationCode' key."

    prompt = f"""
    You are a world-class data analytics consultant for 'PuckPro', an e-commerce brand selling hockey equipment.
    You are given a pandas DataFrame `df` with the schema: {df_schema}.
    The user's business question is: "{user_prompt}"
    {visualization_instruction}
    Your task is to conduct a thorough analysis and present your findings as a strategic, executive-level report in a single JSON object.
    The JSON object must follow this exact structure:
    {{
      "reportTitle": "A concise, executive-level title for the business report.",
      "keyInsights": [{{ "insight": "A critical business insight.", "metric": "The key metric that proves the insight." }}],
      "visualizationCode": "Python code using matplotlib to generate a professional, dark-themed visualization. Use a dark background and light-colored text. Save plot to 'plot.png'. If no plot is possible, return an empty string.",
      "summary": "A strategic narrative that explains the findings and business implications for PuckPro.",
      "stepsTaken": [ "Step 1: Description of the analysis method." ],
      "recommendations": [ "A specific, data-driven, strategic recommendation." ]
    }}
    IMPORTANT ANALYTICAL RULE: You MUST consider the magnitude and statistical significance of your findings.
    Ensure the final output is ONLY the JSON object.
    """
    try:
        response = generative_model.generate_content(prompt)
        raw_text = response.text.strip()
        json_str_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_str_match:
            raise ValueError("The model did not return a valid JSON object.")
        report_data = json.loads(json_str_match.group(0))
        generated_code = report_data.get("visualizationCode", "").strip()
        if generated_code:
            image_buffer = io.BytesIO()
            import numpy as np
            local_vars = {'df': dataframe, 'plt': plt, 'json': json, 'os': os, 'pd': pd, 'np': np}
            try:
                exec(generated_code, {}, local_vars)
                plt.savefig(image_buffer, format='PNG', bbox_inches='tight', transparent=True)
                plt.close()
                if image_buffer.getbuffer().nbytes > 100:
                    image_b64 = base64.b64encode(image_buffer.getvalue()).decode()
                    report_data["visualization"] = f"data:image/png;base64,{image_b64}"
            except Exception as e:
                report_data["code_error"] = f"The visualization code failed: {str(e)}"
        return report_data
    except Exception as e:
        return {"error": f"An error occurred during standard analysis: {str(e)}"}

def run_bayesian_mmm_agent(
    dataframe: pd.DataFrame,
    user_prompt: str,
    dataset_name: str,
    project_id: str = "",
    location: str = "",
    model_name: str = "gemini-2.5-pro",
) -> dict:
    """Run a Bayesian MMM analysis and LLM summary on the provided data.

    This helper orchestrates model training via ``train_and_cache_mmm`` and
    subsequently uses a generative model to create a succinct executive
    summary of the results. The ``dataset_name`` parameter is used to
    name the artifact directory; callers should pass the CSV filename
    (without path) here.

    Args:
        dataframe: A pandas DataFrame loaded from the user-selected dataset.
        user_prompt: The user's business question guiding the analysis.
        dataset_name: Name of the dataset (e.g. ``mmm_advanced_data.csv``) used for artifact naming.
        project_id: Google Cloud project ID used to initialise Vertex AI.
        location: Google Cloud region for Vertex AI.
        model_name: LLM name for generating the summary.

    Returns:
        A dictionary containing the ``model_id``, ``plots`` mapping and
        LLM-generated ``summary``. If training fails, an ``error`` key
        will be present instead.
    """
    # Perform training and artifact generation. We temporarily set the
    # project_id in the call so that the dataset_name is used by
    # train_and_cache_mmm for directory naming. This avoids polluting
    # the output with the actual cloud project.
    train_result = train_and_cache_mmm(
        dataframe,
        project_id=dataset_name,
        location=location,
        model_name=model_name,
    )
    if "error" in train_result:
        return train_result

    model_id = train_result.get("model_id")
    plots = train_result.get("plots", {})
    diagnostics = train_result.get("diagnostics", {})

    # Initialise Vertex AI for generative summarisation if credentials exist
    try:
        vertexai.init(project=project_id, location=location)
        gen_model = GenerativeModel(model_name)
        # Compose a prompt summarising media effectiveness and ROI.
        media_cols = diagnostics.get("media_cols", [])
        effect_vals = diagnostics.get("media_effect_hat", [])
        roi_vals = diagnostics.get("roi_hat", [])
        metrics_str = ", ".join([
            f"{name}: effect={effect:.3f}, ROI={roi:.3f}"
            for name, effect, roi in zip(media_cols, effect_vals, roi_vals)
        ])
        summary_prompt = f"""
You are a senior marketing analyst. The following channels have been fitted
via a Bayesian media mix model: {', '.join(media_cols)}. The resulting
effectiveness and return-on-investment metrics are: {metrics_str}.
The user's business question is: "{user_prompt}".
Write a concise executive summary of the media mix results, highlighting
which channels are most effective, any diminishing returns, and provide
one strategic recommendation. Keep the tone consultative and actionable.
"""
        summary_response = gen_model.generate_content(summary_prompt)
        summary_text = summary_response.text.strip() if summary_response and summary_response.text else ""
    except Exception as exc:
        # If the LLM is unavailable, fall back to a generic summary
        summary_text = (
            "Bayesian media mix model trained successfully. "
            "Refer to the plots for posterior distributions, response curves, "
            "media effectiveness and ROI across channels."
        )

    return {
        "model_id": model_id,
        "plots": plots,
        "diagnostics": diagnostics,
        "summary": summary_text,
    }

def run_follow_up_agent(dataframe: pd.DataFrame, original_prompt: str, follow_up_history_str: str, follow_up_prompt: str, project_id: str, location: str, model_name: str) -> dict:
    vertexai.init(project=project_id, location=location)
    generative_model = GenerativeModel(model_name)
    
    df_schema = get_df_schema(dataframe)
    prompt = f"""
    You are a data analytics consultant continuing a conversation for 'PuckPro'.
    A pandas DataFrame `df` with schema {df_schema} is available.
    The original analysis was for the request: "{original_prompt}"
    The conversation history is: --- {follow_up_history_str} ---
    The user's new follow-up question is: "{follow_up_prompt}"
    Your task is to answer ONLY the newest follow-up question.
    Structure your output as a JSON object: {{"visualizationCode": "Python code for a new plot. Return '' if none.", "summary": "A text-based answer."}}
    Ensure the final output is ONLY the JSON object.
    """
    try:
        response = generative_model.generate_content(prompt)
        raw_text = response.text.strip()
        json_str_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_str_match: raise ValueError("Model did not return valid JSON.")
        report_data = json.loads(json_str_match.group(0))
        generated_code = report_data.get("visualizationCode", "").strip()
        if generated_code:
            image_buffer = io.BytesIO()
            import numpy as np
            local_vars = {'df': dataframe, 'plt': plt, 'json': json, 'os': os, 'pd': pd, 'np': np}
            exec(generated_code, {}, local_vars)
            plt.savefig(image_buffer, format='PNG', bbox_inches='tight', transparent=True)
            plt.close()
            image_b64 = base64.b64encode(image_buffer.getvalue()).decode()
            report_data["visualization"] = f"data:image/png;base64,{image_b64}"
        return report_data
    except Exception as e:
        return {"error": str(e)}
