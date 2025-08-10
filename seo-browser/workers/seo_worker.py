"""Placeholder SEO worker using Playwright.

This module serves as an entrypoint for running browser-based SEO tasks in
the `seo-browser` service. The actual implementation of SEO crawling and
analysis should enqueue jobs from the API and process them here using RQ
and Playwright. At present it simply logs that it has started and
terminates immediately.
"""

def main() -> None:
    print("SEO worker started. No tasks are implemented yet.")


if __name__ == "__main__":
    main()