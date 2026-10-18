import os
import time
import hmac
import hashlib
import logging
import httpx
from datetime import datetime, UTC
from dotenv import load_dotenv
import jwt

load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv()

logger = logging.getLogger(__name__)

# Cache for installation tokens: { installation_id: { "token": str, "expires_at": float } }
_INSTALLATION_TOKEN_CACHE: dict[str, dict] = {}


def get_github_app_jwt() -> str:
    """Generate a short-lived GitHub App JWT signed with RS256 using the app's private key."""
    load_dotenv()
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_raw = os.getenv("GITHUB_APP_PRIVATE_KEY")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")

    if not app_id:
        raise ValueError("GITHUB_APP_ID is not set in environment variables")

    private_key = None
    if private_key_raw:
        # Handle escaped newlines if passed in single-line env var
        private_key = private_key_raw.replace("\\n", "\n")
    elif private_key_path:
        # Clean path (strip quotes)
        cleaned_path = private_key_path.strip("\"'")
        candidates = [
            cleaned_path,
            os.path.join(os.getcwd(), cleaned_path),
            os.path.join(os.getcwd(), "backend", cleaned_path),
            os.path.join(os.path.dirname(__file__), "..", "..", cleaned_path),
            os.path.join(os.path.dirname(__file__), "..", cleaned_path),
        ]
        for path in candidates:
            if os.path.exists(path) and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    private_key = f.read()
                break

    if not private_key:
        # Smart search in backend folder for any .pem / .private-key.pem file
        search_dirs = [
            os.getcwd(),
            os.path.join(os.getcwd(), "backend"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        ]
        for sdir in search_dirs:
            if os.path.exists(sdir) and os.path.isdir(sdir):
                for fname in os.listdir(sdir):
                    if fname.endswith(".pem") or "private-key" in fname:
                        pem_path = os.path.join(sdir, fname)
                        if os.path.isfile(pem_path):
                            with open(pem_path, "r", encoding="utf-8") as f:
                                private_key = f.read()
                            if private_key:
                                break
            if private_key:
                break

    if not private_key:
        raise ValueError(f"Could not load private key from GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH={private_key_path}")

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 480,  # Total span: 540 seconds (9 minutes), strictly within GitHub's 10-minute max
        "iss": app_id,
    }

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded_jwt


async def get_installation_access_token(installation_id: str) -> str:
    """Retrieve a cached installation access token or exchange a new one from GitHub."""
    now = time.time()
    cached = _INSTALLATION_TOKEN_CACHE.get(installation_id)
    if cached and cached["expires_at"] > now + 120:  # 2 minute buffer
        return cached["token"]

    app_jwt = get_github_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OrbitAI-App"
            }
        )

        if res.status_code != 201:
            logger.error("Failed to obtain installation token for %s: %s", installation_id, res.text)
            raise RuntimeError(f"GitHub API Error: {res.status_code} - {res.text}")

        data = res.json()
        token = data["token"]
        expires_at_str = data.get("expires_at")
        if expires_at_str:
            try:
                exp_dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                exp_timestamp = exp_dt.timestamp()
            except Exception:
                exp_timestamp = now + 3500
        else:
            exp_timestamp = now + 3500

        _INSTALLATION_TOKEN_CACHE[installation_id] = {
            "token": token,
            "expires_at": exp_timestamp
        }
        return token


async def list_app_installations() -> list[dict]:
    """Fetch all active installations for this GitHub App."""
    app_jwt = get_github_app_jwt()
    url = "https://api.github.com/app/installations"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OrbitAI-App"
            }
        )
        if res.status_code != 200:
            logger.error("Failed to list app installations: %s", res.text)
            return []
        return res.json()


async def list_installation_repositories(installation_id: str) -> list[dict]:
    """Fetch all repositories accessible by the GitHub App installation."""
    token = await get_installation_access_token(installation_id)
    url = "https://api.github.com/installation/repositories"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OrbitAI-App"
            },
            params={"per_page": 100}
        )


        if res.status_code != 200:
            logger.error("Failed to list repositories for installation %s: %s", installation_id, res.text)
            raise RuntimeError(f"GitHub API Error: {res.status_code} - {res.text}")

        data = res.json()
        return data.get("repositories", [])


def verify_webhook_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Verify that the webhook payload was sent by GitHub using HMAC-SHA256."""
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set; skipping webhook signature verification (DEV ONLY)")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]
    mac = hmac.new(webhook_secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


async def fetch_repository_commits(installation_id: str, owner: str, repo: str, per_page: int = 30) -> list[dict]:
    """Fetch recent commits from GitHub REST API using the installation token."""
    token = await get_installation_access_token(installation_id)
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OrbitAI-App"
            },
            params={"per_page": per_page}
        )
        if res.status_code != 200:
            if res.status_code == 404:
                logger.info("Repository %s/%s commits not accessible (404/not granted)", owner, repo)
            else:
                logger.warning("Failed to fetch commits for %s/%s: %s (%s)", owner, repo, res.status_code, res.text)
            return []
        return res.json()


async def fetch_repository_pull_requests(installation_id: str, owner: str, repo: str, state: str = "all", per_page: int = 30) -> list[dict]:
    """Fetch recent pull requests from GitHub REST API using the installation token."""
    token = await get_installation_access_token(installation_id)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OrbitAI-App"
            },
            params={"state": state, "per_page": per_page}
        )
        if res.status_code != 200:
            if res.status_code == 404:
                logger.info("Repository %s/%s PRs not accessible (404/not granted)", owner, repo)
            else:
                logger.warning("Failed to fetch pull requests for %s/%s: %s (%s)", owner, repo, res.status_code, res.text)
            return []
        return res.json()


async def fetch_single_commit(installation_id: str, owner: str, repo: str, commit_sha: str) -> dict | None:
    """Fetch and validate a single commit SHA from GitHub REST API."""
    try:
        token = await get_installation_access_token(installation_id)
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "OrbitAI-App"
                }
            )
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 404:
                logger.info("Commit %s not found on %s/%s", commit_sha, owner, repo)
                return None
            else:
                logger.warning("Error validating commit %s on %s/%s: %s", commit_sha, owner, repo, res.status_code)
                return None
    except Exception as e:
        logger.warning("Failed to validate commit %s on %s/%s: %s", commit_sha, owner, repo, e)
        return None


