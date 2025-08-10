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
    """Stubbed media mix model training routine.

    In a real deployment this function would train a Bayesian media mix model
    using JAX/NumPyro or a similar framework. To keep the API responsive and
    avoid pulling in heavy dependencies, this stub computes simple summary
    statistics over numeric columns and returns them along with a dummy model
    path. Downstream services can still exercise the job queue and result
    handling.

    Args:
        df: A pandas DataFrame containing the MMM dataset.
        project_id: Not used in this stub but kept for interface compatibility.
        location: Not used in this stub.
        model_name: Not used in this stub.

    Returns:
        A dictionary with a placeholder `cached_model_path` and per-column
        mean values under `metrics`, or an error string if something goes
        wrong.
    """
    try:
        import numpy as np  # Ensure numpy is available
        numeric_cols = df.select_dtypes(include='number').columns
        metrics = {col: float(df[col].mean()) for col in numeric_cols}
        return {
            "cached_model_path": "dummy_model.pkl",
            "metrics": metrics,
        }
    except Exception as e:
        return {"error": str(e)}


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

def run_bayesian_mmm_agent(dataframe: pd.DataFrame, user_prompt: str, revenue_target: float) -> dict:
    return {"reportTitle": "Simulated Bayesian MMM for PuckPro", "summary": "This is a simulated result for the advanced model."}

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
