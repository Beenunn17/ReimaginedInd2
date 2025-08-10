import vertexai
from vertexai.generative_models import GenerativeModel
import re
import json

def generate_social_posts(
    project_id: str,
    location: str,
    brand_name: str,
    user_brief: str,
    selected_strategy: dict
) -> dict:
    """
    Takes a creative strategy and generates social media copy.
    """
    print("Copywriter Agent: Starting process...")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    copywriter_prompt = f"""
    You are an expert social media copywriter for a direct-to-consumer brand called "{brand_name}".
    You have been given a creative strategy for a new campaign. Your task is to write three distinct social media posts that bring this strategy to life.

    **CONTEXT:**
    - **Original User Brief:** "{user_brief}"
    - **Selected Strategic Direction:**
        - Title: "{selected_strategy.get('Title')}"
        - Core Idea: "{selected_strategy.get('Core Idea')}"
        - Description: "{selected_strategy.get('Description')}"

    **YOUR TASK:**
    Write three distinct pieces of copy for a social media post (e.g., for Instagram or Facebook). For each one, provide:
    1.  A compelling **Hook** (the first line to grab attention).
    2.  A short **Body** paragraph that explains the concept.
    3.  A strong **Call to Action (CTA)**.
    4.  A list of 3-5 relevant **Hashtags**.

    Format your response as a valid JSON object with a single key "posts", which is an array of the three post options.
    """

    print("Copywriter Agent: Briefing LLM to generate social media posts...")
    response = model.generate_content(copywriter_prompt)
    raw_llm_text = response.text
    
    json_match = re.search(r'\{.*\}', raw_llm_text, re.DOTALL)
    if not json_match:
        raise ValueError("Copywriter LLM did not return valid JSON.")
    
    parsed_response = json.loads(json_match.group(0))
    return parsed_response