import os
import time
from datetime import datetime

import httpx
from jwt import JWT, jwk_from_pem


class BaseGitHubApp:
    def __init__(self, installation_id: str) -> None:
        self.app_id = os.environ.get("GITHUB_APP_ID")
        self.client_id = os.environ.get("GITHUB_CLIENT_ID")
        self.installation_id = installation_id

        self._jwt_created_at: float = None
        self._jwt: str = None

        self._installation_token_created_at: float = None
        self._installation_token: str = None

        self._user_token_created_at: float = None
        self._user_token: str = None

    def base_github_rest_api(
        self, url: str, method: str = "GET", auth_type: str = "jwt"
    ) -> dict | list | None:
        """Base GitHub REST API.

        Args:
            url (str): The url of the GitHub REST API.
            method (str, optional): The method of the GitHub REST API. Defaults to "GET".
            auth_type (str, optional): The type of the authentication. Defaults to "jwt", can be "jwt" or "install_token" or "user_token".

        Returns:
            dict | list | None: The response of the GitHub REST API.
        """

        auth = ""

        match auth_type:
            case "jwt":
                auth = self.jwt
            case "install_token":
                auth = self.installation_token
            # case "user_token":
            #     auth = self.user_token
            case _:
                raise ValueError(
                    "auth_type must be 'jwt' or 'install_token' or 'user_token'"
                )

        with httpx.Client() as client:
            response = client.request(
                method,
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {auth}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            return response.json()

    @property
    def jwt(self) -> str:
        """Get a JWT for the GitHub App.

        Returns:
            str: A JWT for the GitHub App.
        """
        # 判断是否初始化了 jwt，或者 jwt 是否过期
        if (
            self._jwt is None
            or self._jwt_created_at is None
            or datetime.now().timestamp() - self._jwt_created_at > 60 * 10
        ):
            self._jwt_created_at = datetime.now().timestamp()

            with open(
                os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH", "pem.pem"), "rb"
            ) as pem_file:
                signing_key = jwk_from_pem(pem_file.read())

            payload = {
                # Issued at time
                "iat": int(time.time()),
                # JWT expiration time (10 minutes maximum)
                "exp": int(time.time()) + 600,
                # GitHub App's identifier
                "iss": self.app_id,
            }

            # Create JWT
            jwt_instance = JWT()
            self._jwt = jwt_instance.encode(payload, signing_key, alg="RS256")

        return self._jwt

    @property
    def installation_token(self) -> str:
        """Get an installation token for the GitHub App.

        Returns:
            str: An installation token for the GitHub App.
        """
        if (
            self._installation_token is None
            or self._installation_token_created_at is None
            or datetime.now().timestamp() - self._installation_token_created_at
            > 60 * 60
        ):
            res = self.base_github_rest_api(
                f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
                method="POST",
            )

            self._installation_token_created_at = datetime.now().timestamp()
            self._installation_token = res.get("token", None)

        return self._installation_token

    def get_installation_info(self) -> dict | None:
        """Get installation info

        Returns:
            dict: The installation info.
        """

        return self.base_github_rest_api(
            f"https://api.github.com/app/installations/{self.installation_id}"
        )