# Copilot References

This file tracks external resources, documentation, and code examples used by GitHub Copilot during development.

## 2025-04-26: StreamRip API Integration Update

- **Location:** `src/downloader.py` (import statements and download_track function)
- **Source(s):**
    - Streamrip Scripting Documentation: [https://github.com/nathom/streamrip/wiki/Scripting-with-Streamrip-v2](https://github.com/nathom/streamrip/wiki/Scripting-with-Streamrip-v2)
- **Usage Note:** Updated import statements and API calling patterns to match the official StreamRip v2 API documentation. Changed from using `rip()` function to the recommended `Stream()` class with `download()` method.
