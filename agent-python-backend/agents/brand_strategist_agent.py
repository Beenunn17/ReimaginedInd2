import vertexai
from vertexai.generative_models import GenerativeModel
import re
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright # --- Import Playwright ---

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


async def analyze_brand_with_llm(
    project_id: str,
    location: str,
    brand_name: str,
    website_url: str,
    ad_library_url: str,
    user_brief: str
) -> dict:
    """
    Analyzes brand content using Playwright for fetching and an LLM for strategy.
    """
    print(f"Starting LLM analysis for brand: {brand_name}")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel("gemini-2.5-pro")

    # --- Step 1: Fetch content using Playwright ---
    website_content = await get_text_from_url_playwright(website_url)
    ad_library_content = "No Ad Library URL provided."
    if ad_library_url:
        ad_library_content = await get_text_from_url_playwright(ad_library_url)

    # --- Step 2: Construct the Master Prompt for the LLM ---
    master_prompt = f"""
    You are a world-class brand strategist. Your task is to analyze the provided information and develop three distinct, actionable creative approaches for a new marketing campaign.

    **Brand Information:**
    - **Brand Name:** {brand_name}
    - **User's Creative Brief:** "{user_brief}"
    - **Raw Content from their Website:** "{website_content[:3000]}"
    - **Raw Content from their Meta Ad Library:** "{ad_library_content[:3000]}"

    **Your Task:**
    Based on the information above, generate three creative strategy approaches. For each approach, provide a Title, a Core Idea, and a Description.
    Format your response as a valid JSON object with a single key "approaches". Do not include any text before or after the JSON object.
    """

    # --- Step 3: Call the LLM and robustly parse the response ---
    try:
        print("Sending master prompt to the Gemini LLM...")
        response = model.generate_content(master_prompt)
        raw_llm_text = response.text
        print(f"--- RAW LLM RESPONSE ---\n{raw_llm_text}\n-------------------------")

        json_match = re.search(r'\{.*\}', raw_llm_text, re.DOTALL)
        
        if json_match:
            json_string = json_match.group(0)
            # This will raise an error if the JSON is invalid, which is caught below
            json.loads(json_string)
            llm_response_to_send = json_string
        else:
            # If no JSON is found, the response itself is the error/problem
            llm_response_to_send = raw_llm_text

        return {
            "llm_response": llm_response_to_send,
            "fetched_website_content": website_content[:1000] + "...",
            "fetched_ad_library_content": ad_library_content[:1000] + "..."
        }
    except Exception as e:
        print(f"LLM generation or parsing failed: {e}")
        return {"error": f"LLM generation failed: {e}", "raw_response_on_error": raw_llm_text}