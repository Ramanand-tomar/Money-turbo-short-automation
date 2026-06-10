import time
import requests
import jwt
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from app.services import db
from loguru import logger
import os

class ClerkAuthMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.jwks = None
        self.last_jwks_fetch = 0
        self.clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        self.email_cache = {}
        self.registered_users = set()

        # Build the correct per-instance JWKS URL.
        # Clerk JWTs must be verified against the per-instance JWKS endpoint, not the
        # generic api.clerk.com backend endpoint which does not serve public signing keys.
        #   Format: https://{CLERK_FRONTEND_API_URL}/.well-known/jwks.json
        # CLERK_FRONTEND_API_URL looks like: https://your-app.clerk.accounts.dev
        clerk_frontend_api = os.getenv("CLERK_FRONTEND_API_URL", "").rstrip("/")
        if clerk_frontend_api:
            self.jwks_url = f"{clerk_frontend_api}/.well-known/jwks.json"
        else:
            # Fall back to deriving the domain from the publishable key if available.
            # Publishable keys are formatted: pk_live_<base64-encoded-domain>
            # e.g. pk_live_Y2xlcmsuZXhhbXBsZS5jb20k → clerk.example.com
            pub_key = os.getenv("CLERK_PUBLISHABLE_KEY", "")
            domain = self._extract_domain_from_publishable_key(pub_key)
            if domain:
                self.jwks_url = f"https://{domain}/.well-known/jwks.json"
                logger.info(f"Derived Clerk JWKS URL from publishable key: {self.jwks_url}")
            else:
                self.jwks_url = ""
                logger.error(
                    "CLERK_FRONTEND_API_URL is not set and CLERK_PUBLISHABLE_KEY could not "
                    "be parsed. JWT verification will fail. Set CLERK_FRONTEND_API_URL to "
                    "https://<your-app>.clerk.accounts.dev to resolve this."
                )

    @staticmethod
    def _extract_domain_from_publishable_key(pub_key: str) -> str:
        """
        Clerk publishable keys encode the frontend API domain as a base64 suffix.
        Format: pk_live_<base64(domain + '$')>  or  pk_test_<base64(domain + '$')>
        Returns the decoded domain string, or '' on failure.
        """
        try:
            import base64
            for prefix in ("pk_live_", "pk_test_"):
                if pub_key.startswith(prefix):
                    b64 = pub_key[len(prefix):]
                    # Pad to a multiple of 4
                    b64 += "=" * (-len(b64) % 4)
                    decoded = base64.b64decode(b64).decode("utf-8").rstrip("$").strip()
                    if decoded:
                        return decoded
        except Exception:
            pass
        return ""


    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # Always let CORS preflight (OPTIONS) requests pass through to CORSMiddleware
        # so the browser receives a proper 204 with Access-Control-Allow-* headers.
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Check if route is protected
        is_api_route = path.startswith("/api/v1/")
        exempt_paths = {
            "/api/v1/ping",
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/openapi.json",
            "/api/v1/youtube/oauth-callback"
        }
        
        if not is_api_route or path in exempt_paths:
            await self.app(scope, receive, send)
            return

        # Extract the request origin so we can echo it back in error responses.
        # This is needed because CORSMiddleware runs after us (outer layer) and
        # won't add headers to responses we short-circuit here.
        request_headers = dict(scope.get("headers", []))
        origin = request_headers.get(b"origin", b"").decode("utf-8")

        def _cors_response(status_code: int, content: dict) -> JSONResponse:
            """Build a JSONResponse with CORS headers for cross-origin error cases."""
            resp = JSONResponse(status_code=status_code, content=content)
            if origin:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Headers"] = "*"
                resp.headers["Vary"] = "Origin"
            return resp

        # Try to extract the token from headers or query parameters
        auth_header = request_headers.get(b"authorization", b"").decode("utf-8")
        
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            # Fallback to query parameter
            query_string = scope.get("query_string", b"").decode("utf-8")
            from urllib.parse import parse_qs
            query_params = parse_qs(query_string)
            token_params = query_params.get("token")
            if token_params:
                token = token_params[0]

        if not token:
            # Dev-mode bypass: if Clerk is not configured (no JWKS URL), allow the request
            # through with a warning rather than blocking all traffic during local development.
            # In production, CLERK_FRONTEND_API_URL must always be set.
            if not self.jwks_url:
                logger.warning(
                    f"[DEV MODE] No Clerk JWKS URL configured. Allowing unauthenticated "
                    f"request to '{path}' as user='global'. "
                    "Set CLERK_FRONTEND_API_URL for production auth enforcement."
                )
                if "state" not in scope:
                    scope["state"] = {}
                scope["state"]["user_id"] = "global"
                scope["state"]["clerk_email"] = ""
                scope["state"]["role"] = "user"
                await self.app(scope, receive, send)
                return

            response = _cors_response(401, {"status": 401, "message": "Unauthorized: Missing authentication token"})
            await response(scope, receive, send)
            return

        # Dev-mode bypass: if Clerk JWKS URL is not configured, skip ALL JWT verification.
        # This applies whether or not a token was sent — without a JWKS URL we cannot
        # verify any token, so blocking would make the app unusable locally.
        if not self.jwks_url:
            logger.warning(
                f"[DEV MODE] No Clerk JWKS URL configured. Skipping JWT verification for "
                f"'{path}'. Allowing as user='global'. "
                "Set CLERK_FRONTEND_API_URL in .env for production auth enforcement."
            )
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["user_id"] = "global"
            scope["state"]["clerk_email"] = ""
            scope["state"]["role"] = "user"
            await self.app(scope, receive, send)
            return

        try:
            # Verify token signature
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            if not user_id:
                raise jwt.PyJWTError("Token payload does not contain 'sub' (user_id)")

            # Resolve email
            email = payload.get("email") or payload.get("email_address")
            if not email and self.clerk_secret_key:
                email = self.fetch_clerk_email(user_id)
            if not email:
                email = ""

            # Ensure user exists in db
            if user_id not in self.registered_users:
                db.check_and_create_user(user_id, email)
                self.registered_users.add(user_id)

            user_info = db.get_user(user_id)
            if not user_info:
                # Fallback in case DB query fails temporarily
                user_info = {
                    "role": "user",
                    "is_active": True
                }

            if not user_info.get("is_active", True):
                response = _cors_response(403, {"status": 403, "message": "Forbidden: User account is inactive"})
                await response(scope, receive, send)
                return

            # Inject into request state
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["user_id"] = user_id
            scope["state"]["clerk_email"] = email
            scope["state"]["role"] = user_info.get("role", "user")

        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Clerk JWT expired: {e}")
            response = _cors_response(401, {"status": 401, "message": "Unauthorized: Token has expired"})
            await response(scope, receive, send)
            return
        except jwt.PyJWTError as e:
            logger.warning(f"Clerk JWT validation failed: {e}")
            response = _cors_response(401, {"status": 401, "message": f"Unauthorized: Invalid token ({str(e)})"})
            await response(scope, receive, send)
            return
        except Exception as e:
            logger.error(f"Internal error during auth: {e}")
            response = _cors_response(500, {"status": 500, "message": "Internal server error during authentication"})
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)



    def get_jwks(self):
        if not self.jwks_url:
            raise jwt.PyJWTError(
                "Clerk JWKS URL is not configured. Set the CLERK_FRONTEND_API_URL "
                "environment variable to https://<your-app>.clerk.accounts.dev"
            )
        now = time.time()
        # Cache for 24 hours (86400 seconds)
        if not self.jwks or (now - self.last_jwks_fetch > 86400):
            try:
                resp = requests.get(self.jwks_url, timeout=10)
                resp.raise_for_status()
                self.jwks = resp.json()
                self.last_jwks_fetch = now
                logger.info("Successfully fetched and cached Clerk JWKS keys.")
            except Exception as e:
                logger.error(f"Failed to fetch Clerk JWKS from {self.jwks_url}: {e}")
                if not self.jwks:
                    raise e
        return self.jwks

    def verify_token(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise jwt.PyJWTError("Token header does not contain 'kid'")

        jwks = self.get_jwks()
        jwk = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                jwk = key
                break

        if not jwk:
            raise jwt.PyJWTError(f"Key with kid {kid} not found in Clerk JWKS")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        decoded = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})
        return decoded

    def fetch_clerk_email(self, user_id: str) -> str:
        if user_id in self.email_cache:
            return self.email_cache[user_id]

        try:
            headers = {
                "Authorization": f"Bearer {self.clerk_secret_key}",
                "Content-Type": "application/json"
            }
            resp = requests.get(f"https://api.clerk.com/v1/users/{user_id}", headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                email_addresses = data.get("email_addresses", [])
                if email_addresses:
                    email = email_addresses[0].get("email_address")
                    self.email_cache[user_id] = email
                    return email
        except Exception as e:
            logger.error(f"Failed to fetch email for user {user_id} from Clerk Backend API: {e}")
        return None
