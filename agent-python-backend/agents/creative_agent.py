# agents/creative_agent.py
import os, base64
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel, Image

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
_MODEL = None

def _ensure_vertex(project_id: str | None = None, location: str | None = None) -> ImageGenerationModel:
    global _MODEL
    if _MODEL is None:
        pid = project_id or PROJECT_ID
        loc = location or LOCATION
        if not pid:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")
        vertexai.init(project=pid, location=loc)
        _MODEL = ImageGenerationModel.from_pretrained("imagen-4.0-ultra-generate-preview-06-06")
    return _MODEL

def _image_from_data_url(data_url: str) -> Image:
    # expects data:image/png;base64,AAAA...
    _, b64 = data_url.split(",", 1)
    return Image.from_bytes(base64.b64decode(b64))

def _build_prompt(components: dict) -> str:
    parts = [
        components.get("customSubject", ""),
        components.get("sceneDescription", ""),
        components.get("imageType", ""),
        components.get("style", ""),
        components.get("camera", ""),
        components.get("lighting", ""),
        components.get("composition", ""),
        components.get("modifiers", ""),
    ]
    neg = components.get("negativePrompt")
    if neg:
        parts.append(f"NEGATIVE: {neg}")
    return ", ".join([p for p in parts if p])

def generate_ad_creative(
    project_id: str,
    location: str,
    platform: str,
    prompt_components: dict,
    subject_image_b64: str | None = None,
    scene_image_b64: str | None = None,
    n: int = 4,
    seed: int | None = None,
) -> dict:
    """
    Calls Imagen with sample_count=1 per request (the only value allowed)
    and loops n times to return up to n images.
    """
    model = _ensure_vertex(project_id, location)
    prompt = _build_prompt(prompt_components)
    aspect = "1:1" if (platform or "").lower() == "meta" else "9:16"

    has_subject = bool(subject_image_b64)
    has_scene = bool(scene_image_b64)

    images_data_urls: list[str] = []

    # Helper to convert SDK image -> data URL
    def _to_data_url(img_obj) -> str:
        img_bytes = getattr(img_obj, "image_bytes", None) or getattr(img_obj, "_image_bytes", None)
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    # Loop because prebuilt model only returns 1 image per request
    tries = max(1, int(n or 1))
    for i in range(tries):
        if not has_subject and not has_scene:
            # TEXT → IMAGE
            result = model.generate_images(
                prompt=prompt,
                aspect_ratio=aspect,
                seed=seed if seed is not None else None,
                # number_of_images is NOT allowed >1; omit or set to 1
            )
        else:
            # IMAGE EDIT — use exactly one base image
            base_img = _image_from_data_url(subject_image_b64 or scene_image_b64)  # type: ignore[arg-type]
            result = model.edit_image(
                prompt=prompt,
                image=base_img,
                seed=seed if seed is not None else None,
            )

        if getattr(result, "images", None):
            images_data_urls.append(_to_data_url(result.images[0]))

    if not images_data_urls:
        raise RuntimeError("No images returned by model.")

    return {"image_urls": images_data_urls}
