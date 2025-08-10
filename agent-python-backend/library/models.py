"""Pydantic models and data schemas for the creative library.

This module defines Pydantic models that may be used by FastAPI endpoints.
Currently this file contains only placeholders to illustrate where data
schemas would be declared. Extend these classes as needed when adding
functionality to the creative library.
"""

from __future__ import annotations

from pydantic import BaseModel


class ImageSaveResponse(BaseModel):
    """Response returned after saving an image.

    Attributes:
        thumb: URL to the thumbnail version of the saved image.
        medium: URL to the medium-sized version of the saved image.
        orig: URL to the original image.
    """

    thumb: str
    medium: str
    orig: str