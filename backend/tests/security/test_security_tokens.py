"""Customer sessions are opaque cookies, not JWTs minted by core.security."""
import app.core.security as security
from app.identity.jwt import new_token, token_hash


def test_session_token_is_opaque_and_not_a_jwt():
    assert not hasattr(security, "create_access_token")
    assert not hasattr(security, "decode_access_token")
    token = new_token()
    digest = token_hash(token)
    assert digest == token_hash(token)
    assert digest != token
