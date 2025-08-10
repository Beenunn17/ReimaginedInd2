import vertexai
from vertexai.generative_models import GenerativeModel
import re
import json
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from . import creative_agent # We need to call our existing creative agent

async def get_text_from_url_playwright(url: str) -> str:
    """Uses Playwright to fetch and parse text content from a URL."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            html_content = await page.content()
            await browser.close()
            soup = BeautifulSoup(html_content, 'html.parser')
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return '\n'.join(chunk for chunk in chunks if chunk)
    except Exception as e:
        print(f"Playwright failed to fetch {url}: {e}")
        return f"An error occurred while fetching the content: {e}"

async def brief_to_prompts_and_assets(
    project_id: str,
    location: str,
    brand_name: str,
    website_url: str,
    ad_library_url: str,
    user_brief: str,
    selected_strategy: dict
) -> dict:
    """
    Takes a strategic brief, performs deep analysis, generates detailed prompts,
    and then creates visual assets.
    """
    print("Creative Director Agent: Starting process...")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    # --- Step 1: Fetch content again for deep analysis ---
    website_content = await get_text_from_url_playwright(website_url)
    ad_library_content = "No Ad Library URL provided."
    if ad_library_url:
        ad_library_content = await get_text_from_url_playwright(ad_library_url)

    # --- Step 2: Master Prompt for the Creative Director LLM ---
    # This prompt asks the LLM to perform the deep analysis you suggested.
    creative_director_prompt = f"""
    You are an expert Creative Director. You have been given a high-level strategy and raw content from a brand's website and ad library.
    Your task is to first perform a deep analysis and then generate four distinct, detailed, and diverse image generation prompts for social media ads.

    **CONTEXT:**
    - **Brand Name:** {brand_name}
    - **Original User Brief:** "{user_brief}"
    - **Selected Strategic Direction:**
        - Title: "{selected_strategy.get('Title')}"
        - Core Idea: "{selected_strategy.get('Core Idea')}"
    - **Website Content:** "{website_content[:2000]}"
    - **Ad Library Content:** "{ad_library_content[:2000]}"

    **ANALYSIS TASK (Internal Monologue):**
    1.  **Visual Language:** Based on the website/ad content, what is the brand's visual style? (e.g., "minimalist, earthy tones, natural light", "bold, high-contrast, energetic").
    2.  **Brand Voice:** What is the tone of the copy? (e.g., "witty and direct", "aspirational and serene").
    3.  **Ad Formats:** What patterns do you see in their ads? (e.g., "product-focused studio shots", "user-generated lifestyle content").

    **PROMPT GENERATION TASK:**
    Based on your analysis, create four image generation prompts that bring the "Selected Strategic Direction" to life.
    - Each prompt must be unique.
    - Each prompt must be highly detailed, specifying subject, scene, style, camera details, lighting, and composition.
    - The prompts must align with the brand's existing visual language and voice.

    Return your response as a valid JSON object with a single key "prompts", which is an array of four prompt strings. Do not include any other text or your analysis monologue.
    """

    print("Creative Director Agent: Briefing LLM to generate prompts...")
    response = model.generate_content(creative_director_prompt)
    raw_llm_text = response.text
    
    json_match = re.search(r'\{.*\}', raw_llm_text, re.DOTALL)
    if not json_match:
        raise ValueError("Creative Director LLM did not return valid JSON for prompts.")
    
    parsed_response = json.loads(json_match.group(0))
    generated_prompts = parsed_response.get("prompts", [])
    
    if not generated_prompts:
        raise ValueError("Creative Director LLM did not generate any prompts.")

    print(f"Creative Director Agent: Generated {len(generated_prompts)} prompts. Now creating assets...")

    # --- Step 3: Call the Creative Agent for each generated prompt ---
    # We will generate one image for each of the four prompts.
    image_urls = []
    for prompt in generated_prompts:
        # We re-use the components from the Manual Mode for consistency
        prompt_components = {
            "customSubject": brand_name,
            "sceneDescription": prompt, # The LLM's output is the scene description
            "imageType": 'Product Photo',
            "style": 'Photorealistic',
            "camera": '85mm',
            "lighting": 'Studio Lighting',
            "composition": 'Centered',
            "modifiers": 'Ultra detailed',
            "negativePrompt": 'Low quality, blurry, watermark'
        }
        
        # Call the original creative agent
        asset_data = creative_agent.generate_ad_creative(
            project_id=project_id,
            location=location,
            platform="meta", # Default to meta for now
            prompt_components=prompt_components,
        )
        if asset_data and asset_data.get("image_urls"):
            # generate_ad_creative returns a list, we just want the first one here
            image_urls.append(asset_data["image_urls"][0])

    return {"image_urls": image_urls}