"""OAuth helpers for YouTube Data API requests."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.services.youtube.models import OAuthToken, YouTubeOAuthCredentials


class YouTubeOAuthError(RuntimeError):
    """Raised when OAuth token refresh fails."""


class GoogleOAuthClient:
    """Refresh OAuth access tokens for YouTube uploads."""

    def __init__(
        self,
        credentials: YouTubeOAuthCredentials,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.credentials = credentials
        self._client = client
        self.timeout = timeout

    def build_authorization_url(
        self,
        *,
        authorization_endpoint: str = "https://accounts.google.com/o/oauth2/v2/auth",
        redirect_uri: str,
        state: str | None = None,
        access_type: str = "offline",
        prompt: str = "consent",
    ) -> str:
        """Build a consent URL for obtaining the first refresh token."""
        self.credentials.validate()
        params = {
            "client_id": self.credentials.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.credentials.scope,
            "access_type": access_type,
            "prompt": prompt,
        }
        if state:
            params["state"] = state
        return f"{authorization_endpoint}?{urlencode(params)}"

    async def refresh_access_token(self) -> OAuthToken:
        """Exchange the configured refresh token for a short-lived access token."""
        self.credentials.validate()
        payload = {
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "refresh_token": self.credentials.refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    self.credentials.token_uri,
                    data=payload,
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.credentials.token_uri,
                        data=payload,
                        headers={"content-type": "application/x-www-form-urlencoded"},
                    )
        except httpx.HTTPError as exc:
            raise YouTubeOAuthError(f"OAuth token refresh failed: {exc}") from exc

        if response.status_code >= 400:
            raise YouTubeOAuthError(
                f"OAuth token refresh failed with HTTP {response.status_code}: "
                f"{response.text}"
            )

        body = response.json()
        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise YouTubeOAuthError("OAuth token response did not include access_token.")

        return OAuthToken(
            access_token=access_token,
            token_type=str(body.get("token_type") or "Bearer"),
            expires_in=body.get("expires_in"),
            scope=body.get("scope"),
        )
