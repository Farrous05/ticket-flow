"""
GitHub integration service for creating issues from bug reports.
"""

import httpx

from src.common.config import get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def create_github_issue(
    title: str,
    description: str,
    priority: str,
    ticket_id: str | None = None
) -> dict:
    """
    Create a GitHub issue for a bug report.

    Args:
        title: Issue title
        description: Issue description/body
        priority: Priority level ('low', 'medium', 'high', 'critical')
        ticket_id: Optional ticket ID for reference

    Returns:
        Dict with success status, issue number, and URL (or error message)
    """
    if not settings.github_token or not settings.github_repo:
        logger.info("github_not_configured")
        return {
            "success": False,
            "error": "GitHub integration not configured. Set GITHUB_TOKEN and GITHUB_REPO environment variables.",
            "configured": False
        }

    # Map priority to GitHub labels
    priority_labels = {
        "critical": ["bug", "priority: critical"],
        "high": ["bug", "priority: high"],
        "medium": ["bug", "priority: medium"],
        "low": ["bug", "priority: low"]
    }

    labels = priority_labels.get(priority, ["bug"])

    # Build issue body with metadata
    body = f"""## Bug Report

**Priority:** {priority.upper()}
**Source:** Support Ticket Agent

---

{description}

---
*Created automatically from support ticket{f' `{ticket_id}`' if ticket_id else ''}*
"""

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"https://api.github.com/repos/{settings.github_repo}/issues",
                headers={
                    "Authorization": f"Bearer {settings.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json={
                    "title": title,
                    "body": body,
                    "labels": labels
                }
            )

            if response.status_code == 201:
                data = response.json()
                logger.info(
                    "github_issue_created",
                    issue_number=data["number"],
                    url=data["html_url"]
                )
                return {
                    "success": True,
                    "issue_number": data["number"],
                    "issue_url": data["html_url"],
                    "repo": settings.github_repo
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(
                    "github_issue_failed",
                    status=response.status_code,
                    error=error_msg
                )
                return {
                    "success": False,
                    "error": f"GitHub API error ({response.status_code}): {error_msg}"
                }

    except httpx.TimeoutException:
        logger.error("github_timeout")
        return {"success": False, "error": "GitHub API request timed out"}
    except Exception as e:
        logger.error("github_exception", error=str(e))
        return {"success": False, "error": str(e)}
