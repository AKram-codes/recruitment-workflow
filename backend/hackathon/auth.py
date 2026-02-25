import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.core import signing
from django.utils import timezone


SESSION_TTL = timedelta(days=7)
OTP_CHALLENGE_TTL = timedelta(minutes=5)


class ExternalAuthError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = (os.getenv(name) or '').strip()
    if not value:
        raise ExternalAuthError(f'Missing {name} environment variable')
    return value


def post_form_json(*, url: str, payload: dict[str, str], timeout: int = 15) -> dict:
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
    }

    raw = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=raw, method='POST', headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, 'status', None) or resp.getcode()
            body = resp.read().decode('utf-8')
            if status < 200 or status >= 300:
                raise ExternalAuthError(f'External auth returned HTTP {status}')
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError as exc:
                raise ExternalAuthError('External auth returned invalid JSON') from exc
            if not isinstance(parsed, dict):
                raise ExternalAuthError('External auth returned invalid response')
            return parsed
    except urllib.error.HTTPError as exc:
        raise ExternalAuthError(f'External auth returned HTTP {exc.code}') from exc
    except urllib.error.URLError as exc:
        raise ExternalAuthError('Unable to reach external auth service') from exc


def _is_success_response(payload: dict) -> bool:
    if 'success' in payload:
        return bool(payload.get('success'))

    status = payload.get('status')
    if status is None:
        return False

    status_str = str(status).strip().lower()
    return status_str in {'success', 'ok', 'true', '1'}


def require_env(name: str) -> str:
    return _require_env(name)


def is_success_response(payload: dict) -> bool:
    return _is_success_response(payload)


def create_signed_session(*, payload: dict) -> tuple[str, timezone.datetime]:
    token = signing.dumps(payload, salt='hackathon.session')
    expires_at = timezone.now() + SESSION_TTL
    return token, expires_at


def load_signed_session(token: str) -> dict:
    try:
        data = signing.loads(token, salt='hackathon.session', max_age=int(SESSION_TTL.total_seconds()))
    except signing.SignatureExpired as exc:
        raise ExternalAuthError('Session expired') from exc
    except signing.BadSignature as exc:
        raise ExternalAuthError('Invalid session token') from exc

    if not isinstance(data, dict):
        raise ExternalAuthError('Invalid session token')
    return data


def create_signed_otp_challenge(*, email: str, channel: str) -> tuple[str, timezone.datetime]:
    token = signing.dumps({'email': email, 'channel': channel}, salt='hackathon.otp')
    expires_at = timezone.now() + OTP_CHALLENGE_TTL
    return token, expires_at


def load_signed_otp_challenge(token: str) -> dict:
    try:
        data = signing.loads(token, salt='hackathon.otp', max_age=int(OTP_CHALLENGE_TTL.total_seconds()))
    except signing.SignatureExpired as exc:
        raise ExternalAuthError('Invalid or expired OTP.') from exc
    except signing.BadSignature as exc:
        raise ExternalAuthError('Invalid or expired OTP.') from exc

    if not isinstance(data, dict):
        raise ExternalAuthError('Invalid or expired OTP.')
    return data
