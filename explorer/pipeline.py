"""
Custom social-auth-app-django pipeline steps.

These steps run after the standard pipeline to perform application-specific
actions like encrypting and storing the GitHub access token.
"""

import logging

from explorer.encryption import TokenEncryptionService

logger = logging.getLogger(__name__)


def store_encrypted_token(backend, user, response, *args, **kwargs):
    """Pipeline step: encrypt and store the GitHub access token on the User model.

    This step runs after successful OAuth authentication. It takes the access
    token from the OAuth response, encrypts it using Fernet symmetric encryption,
    and stores the encrypted bytes on the user's `github_token_encrypted` field.

    Args:
        backend: The social auth backend (e.g., GithubOAuth2).
        user: The authenticated User instance.
        response: The OAuth response dict containing 'access_token'.
        *args: Additional positional arguments from the pipeline.
        **kwargs: Additional keyword arguments from the pipeline.
    """
    if backend.name != "github":
        return

    access_token = response.get("access_token")
    if not access_token:
        logger.warning(
            "No access_token in GitHub OAuth response for user %s", user.username
        )
        return

    try:
        encryption_service = TokenEncryptionService()
        encrypted_token = encryption_service.encrypt(access_token)
        user.github_token_encrypted = encrypted_token
        user.save(update_fields=["github_token_encrypted"])
        logger.info("Stored encrypted GitHub token for user %s", user.username)
    except Exception as e:
        logger.error(
            "Failed to encrypt/store GitHub token for user %s: %s",
            user.username,
            str(e),
        )
