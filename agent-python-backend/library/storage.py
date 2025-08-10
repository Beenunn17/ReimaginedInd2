"""Storage backend abstraction for image bytes.

This module provides a simple interface for saving binary data and
generating signed URLs. In development, it writes files to the local
filesystem under a configurable base directory and returns relative URLs
rooted at `/image_library/`. In production, it can be switched to use
Google Cloud Storage by setting the environment variable
`STORAGE_BACKEND=gcs` and providing a `GCS_BUCKET`. The GCS
implementation is intentionally left unimplemented in this example to
avoid pulling in heavy dependencies when running locally. To add GCS
support, install `google-cloud-storage` and implement the TODOs.

Environment variables:
    STORAGE_BACKEND: 'local' (default) or 'gcs'.
    GCS_BUCKET: Name of the Google Cloud Storage bucket to use when
        STORAGE_BACKEND is 'gcs'.
    IMAGE_LIBRARY_DIR: Base directory for local storage (default
        './image_library').
"""

from __future__ import annotations

import os
from typing import Optional

STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local").lower()
GCS_BUCKET: str = os.getenv("GCS_BUCKET", "")
IMAGE_LIBRARY_DIR: str = os.getenv("IMAGE_LIBRARY_DIR", "./image_library")


def _ensure_dir(path: str) -> None:
    """Create parent directories for the given path if they do not exist."""
    os.makedirs(path, exist_ok=True)


def save_bytes(path: str, data: bytes) -> str:
    """Persist a byte string to the configured storage backend.

    Args:
        path: Relative path (within the image library) at which to store the
            bytes. For example, 'orig/1234.jpg'.
        data: Raw byte content to write.

    Returns:
        A URL string that can be used by the frontend to retrieve the data.

    Raises:
        NotImplementedError: If the GCS backend is configured but not
            implemented.
    """
    if STORAGE_BACKEND == "gcs":
        # TODO: implement GCS file upload and return a signed URL.
        raise NotImplementedError(
            "GCS backend is not implemented in this local environment. "
            "Install google-cloud-storage and implement save_bytes()."
        )
    # Local storage backend
    dest_path = os.path.join(IMAGE_LIBRARY_DIR, path)
    _ensure_dir(os.path.dirname(dest_path))
    with open(dest_path, "wb") as f:
        f.write(data)
    # Return a relative URL pointing to where the file will be served
    return f"/image_library/{path}".replace("\\", "/")


def signed_url(path: str, expires_seconds: int = 3600) -> str:
    """Generate a signed URL for the given path.

    For the local backend, this simply prefixes the path with `/image_library/`.
    For GCS, a time-limited signed URL should be generated. This function is
    intentionally a stub for the GCS case to avoid external dependencies.

    Args:
        path: Relative path within the image library.
        expires_seconds: Expiration time for the signed URL (unused for local).

    Returns:
        A URL string that can be used by clients to fetch the resource.

    Raises:
        NotImplementedError: If the GCS backend is configured but not
            implemented.
    """
    if STORAGE_BACKEND == "gcs":
        # TODO: generate a signed URL using google-cloud-storage.
        raise NotImplementedError(
            "GCS signed URL generation is not implemented. "
            "Install google-cloud-storage and implement signed_url()."
        )
    # Local storage: return relative URL
    return f"/image_library/{path}".replace("\\", "/")