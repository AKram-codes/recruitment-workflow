import json
import re
from datetime import date, timedelta

from django.db import IntegrityError, connection, transaction
from django.http import HttpRequest, JsonResponse
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .auth import (
    ExternalAuthError,
    create_signed_otp_challenge,
    create_signed_session,
    is_success_response,
    load_signed_otp_challenge,
    load_signed_session,
    post_form_json,
    require_env,
)

SYSTEM_NAME = 'isl'
REGISTER_ROLE = 'isl_user'


def _normalize_phone(raw: str) -> str:
    return re.sub(r'\D+', '', (raw or '').strip())


def _get_bearer_token(request: HttpRequest) -> str | None:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None

    prefix = 'Bearer '
    if not auth_header.startswith(prefix):
        return None

    token = auth_header[len(prefix) :].strip()
    return token or None


def _get_session_payload(request: HttpRequest) -> dict | None:
    token = _get_bearer_token(request)
    if not token:
        return None
    try:
        return load_signed_session(token)
    except ExternalAuthError:
        return None


def _json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return {}


def _external_error_message(result: dict, default: str) -> str:
    return result.get('error') or result.get('message') or default


def _external_success_message(result: dict) -> str | None:
    message = (result.get('message') or result.get('status') or '').strip()
    return message or None


def _post_external_or_error(
    *,
    url_env: str,
    payload: dict[str, str],
    failure_status: int,
    failure_default_message: str,
) -> tuple[dict | None, JsonResponse | None]:
    try:
        url = require_env(url_env)
    except ExternalAuthError as exc:
        return None, JsonResponse({'error': str(exc)}, status=500)

    try:
        result = post_form_json(url=url, payload=payload)
    except ExternalAuthError as exc:
        return None, JsonResponse({'error': str(exc)}, status=502)

    if not is_success_response(result):
        message = _external_error_message(result, failure_default_message)
        return None, JsonResponse({'error': message}, status=failure_status)

    return result, None


class HealthView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse({'status': 'ok'})


class ApiLoginView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        payload = _json_body(request)
        username_raw = (payload.get('username') or '').strip()
        password = (payload.get('password') or '').strip()

        if not username_raw or not password:
            return JsonResponse({'error': 'Please enter username and password.'}, status=400)

        result, error = _post_external_or_error(
            url_env='LOGIN_THROUGH_PASSWORD_URL',
            payload={
                'email': username_raw,
                'password': password,
                'system_name': SYSTEM_NAME,
            },
            failure_status=401,
            failure_default_message='Invalid username or password.',
        )
        if error:
            return error

        session_payload = {'email': username_raw}
        session_payload.update(result or {})
        raw_token, expires_at = create_signed_session(payload=session_payload)

        return JsonResponse(
            {
                'token': raw_token,
                'expires_at': expires_at.isoformat(),
                'user': {
                    'id': None,
                    'username': username_raw,
                },
            }
        )


class ApiForgotPasswordView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        payload = _json_body(request)
        email = (payload.get('email') or '').strip()
        password = (payload.get('password') or '').strip()

        if not email or not password:
            return JsonResponse({'error': 'Please enter email and password.'}, status=400)

        result, error = _post_external_or_error(
            url_env='FORGET_PASSWORD_URL',
            payload={
                'email': email,
                'password': password,
                'system_name': SYSTEM_NAME,
            },
            failure_status=400,
            failure_default_message='Unable to reset password.',
        )
        if error:
            return error

        return JsonResponse({'ok': True, 'message': _external_success_message(result or {})})


class ApiRegisterView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        payload = _json_body(request)
        display_name = (payload.get('display_name') or '').strip()
        email = (payload.get('email') or '').strip()
        phone_number = _normalize_phone(payload.get('phone_number') or '')
        password = (payload.get('password') or '').strip()

        if not display_name or not email or not phone_number or not password:
            return JsonResponse({'error': 'Please fill all required fields.'}, status=400)

        result, error = _post_external_or_error(
            url_env='REGISTER_URL',
            payload={
                'display_name': display_name,
                'email': email,
                'phone_number': phone_number,
                'password': password,
                'system_name': SYSTEM_NAME,
                'role': REGISTER_ROLE,
            },
            failure_status=400,
            failure_default_message='Unable to create account.',
        )
        if error:
            return error

        return JsonResponse({'ok': True, 'message': _external_success_message(result or {})})


class ApiMeView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        session_payload = _get_session_payload(request)
        if session_payload is None:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        email = (session_payload.get('email') or '').strip() or None

        return JsonResponse(
            {
                'user': {
                    'id': None,
                    'username': email,
                },
                'member': {
                    'id': None,
                    'name': session_payload.get('display_name'),
                    'email': email,
                    'phone': session_payload.get('phone_number'),
                },
            }
        )


class ApiLogoutView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse({'ok': True})


class ApiOtpRequestView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        payload = _json_body(request)
        channel = (payload.get('channel') or '').strip().lower()
        phone = _normalize_phone(payload.get('phone') or payload.get('username') or '')
        email = (payload.get('email') or payload.get('username') or '').strip()

        if channel not in {'whatsapp', 'email'}:
            return JsonResponse({'error': 'Invalid OTP channel.'}, status=400)

        if channel == 'whatsapp' and not phone:
            return JsonResponse({'error': 'Please enter mobile number.'}, status=400)
        if channel == 'email' and not email:
            return JsonResponse({'error': 'Please enter email id.'}, status=400)

        identifier = email if channel == 'email' else phone
        result, error = _post_external_or_error(
            url_env='SEND_OTP_URL',
            payload={
                'email': identifier,
                'type': channel,
                'system_name': SYSTEM_NAME,
            },
            failure_status=400,
            failure_default_message='Unable to request key',
        )
        if error:
            return error

        challenge_id, expires_at = create_signed_otp_challenge(email=identifier, channel=channel)
        return JsonResponse({'challenge_id': challenge_id, 'expires_at': expires_at.isoformat()})


class ApiOtpVerifyView(View):
    def post(self, request: HttpRequest) -> JsonResponse:
        payload = _json_body(request)
        challenge_id = payload.get('challenge_id')
        otp = (payload.get('otp') or '').strip()

        if not challenge_id or not otp:
            return JsonResponse({'error': 'Please enter OTP.'}, status=400)

        try:
            otp_payload = load_signed_otp_challenge(str(challenge_id))
        except ExternalAuthError as exc:
            return JsonResponse({'error': str(exc)}, status=401)

        email = (otp_payload.get('email') or '').strip()
        result, error = _post_external_or_error(
            url_env='VERIFY_OTP_URL',
            payload={
                'email': email,
                'otp': otp,
                'system_name': SYSTEM_NAME,
            },
            failure_status=401,
            failure_default_message='Invalid or expired OTP.',
        )
        if error:
            return error

        session_payload = {'email': email}
        session_payload.update(result or {})
        raw_token, expires_at = create_signed_session(payload=session_payload)

        return JsonResponse(
            {
                'token': raw_token,
                'expires_at': expires_at.isoformat(),
                'user': {'id': None, 'username': email},
            }
        )


def _api_success(*, data: dict | list | None = None, message: str = 'Success', status_code: int = status.HTTP_200_OK) -> Response:
    payload: dict[str, object] = {'success': True, 'message': message}
    if data is not None:
        payload['data'] = data
    return Response(payload, status=status_code)


def _api_error(
    *,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    errors: dict[str, str] | None = None,
) -> Response:
    payload: dict[str, object] = {'success': False, 'message': message}
    if errors:
        payload['errors'] = errors
    return Response(payload, status=status_code)


def _normalize_name(value: object) -> str:
    return str(value or '').strip()


def _parse_employee_date(raw_value: object, *, field: str, required: bool = True) -> tuple[date | None, str | None]:
    value = str(raw_value or '').strip()
    if not value:
        if required:
            return None, f'{field} is required and must be in YYYY-MM-DD format.'
        return None, None

    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f'{field} must be in YYYY-MM-DD format.'


def _row_to_employee(row: tuple) -> dict[str, object]:
    emp_id, first_name, middle_name, last_name, start_date, end_date = row
    full_name_parts = [first_name, middle_name, last_name]
    full_name = ' '.join(part for part in full_name_parts if part)

    return {
        'emp_id': emp_id,
        'first_name': first_name,
        'middle_name': middle_name,
        'last_name': last_name,
        'full_name': full_name,
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None,
        'lifecycle_status': 'active' if end_date is None else 'exited',
    }


def _fetch_employee_row(emp_id: int, cursor=None) -> tuple | None:
    query = '''
        SELECT emp_id, first_name, middle_name, last_name, start_date, end_date
        FROM emp_master
        WHERE emp_id = %s
    '''

    if cursor is not None:
        cursor.execute(query, [emp_id])
        return cursor.fetchone()

    with connection.cursor() as local_cursor:
        local_cursor.execute(query, [emp_id])
        return local_cursor.fetchone()


def _employee_counts() -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT
                COUNT(*) AS total_count,
                SUM(CASE WHEN end_date IS NULL THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN end_date IS NOT NULL THEN 1 ELSE 0 END) AS exited_count
            FROM emp_master
            '''
        )
        total_count, active_count, exited_count = cursor.fetchone()

    return {
        'total': int(total_count or 0),
        'active': int(active_count or 0),
        'exited': int(exited_count or 0),
    }


def _employee_profile_data(emp_id: int) -> dict[str, object] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT emp_id, first_name, middle_name, last_name, start_date, end_date
            FROM emp_master
            WHERE emp_id = %s
            ''',
            [emp_id],
        )
        personal_row = cursor.fetchone()
        if personal_row is None:
            return None

        cursor.execute(
            '''
            SELECT bank_name, branch_name, bank_acct_no, ifsc_code
            FROM emp_bank_info
            WHERE emp_id = %s
            LIMIT 1
            ''',
            [emp_id],
        )
        bank_row = cursor.fetchone()

        cursor.execute(
            '''
            SELECT pan, aadhaar, uan_epf_acctno, esi
            FROM emp_reg_info
            WHERE emp_id = %s
            LIMIT 1
            ''',
            [emp_id],
        )
        registration_row = cursor.fetchone()

        cursor.execute(
            '''
            SELECT comp_type, status, doc_url
            FROM emp_compliance_tracker
            WHERE emp_id = %s
            ORDER BY emp_compliance_tracker_id DESC
            ''',
            [emp_id],
        )
        compliance_rows = cursor.fetchall()

        cursor.execute(
            '''
            SELECT int_title, ext_title, main_level, sub_level, start_of_ctc, end_of_ctc, ctc_amt
            FROM emp_ctc_info
            WHERE emp_id = %s
            ORDER BY start_of_ctc DESC, emp_ctc_id DESC
            ''',
            [emp_id],
        )
        ctc_rows = cursor.fetchall()

    personal = _row_to_employee(personal_row)
    bank = None
    if bank_row is not None:
        bank = {
            'bank_name': bank_row[0],
            'branch_name': bank_row[1],
            'bank_acct_no': bank_row[2],
            'ifsc_code': bank_row[3],
        }

    registration_ids = {
        'pan': None,
        'aadhaar': None,
        'uan_epf_acctno': None,
        'esi': None,
    }
    if registration_row is not None:
        registration_ids = {
            'pan': registration_row[0],
            'aadhaar': registration_row[1],
            'uan_epf_acctno': registration_row[2],
            'esi': registration_row[3],
        }

    compliance_tracker = [
        {
            'comp_type': row[0],
            'status': row[1],
            'doc_url': row[2],
        }
        for row in compliance_rows
    ]

    ctc_timeline = [
        {
            'int_title': row[0],
            'ext_title': row[1],
            'main_level': int(row[2]) if row[2] is not None else None,
            'sub_level': row[3],
            'start_of_ctc': row[4].isoformat() if row[4] else None,
            'end_of_ctc': row[5].isoformat() if row[5] else None,
            'ctc_amt': int(row[6]) if row[6] is not None else None,
        }
        for row in ctc_rows
    ]

    missing_sections = []
    if bank is None:
        missing_sections.append('bank')
    if registration_row is None:
        missing_sections.append('compliance.registration_ids')
    if not compliance_tracker:
        missing_sections.append('compliance.tracker')
    if not ctc_timeline:
        missing_sections.append('ctc_timeline')

    return {
        'emp_id': personal['emp_id'],
        'personal': personal,
        'bank': bank,
        'compliance': {
            'registration_ids': registration_ids,
            'tracker': compliance_tracker,
        },
        'ctc_timeline': ctc_timeline,
        'missing_sections': missing_sections,
    }


@api_view(['GET', 'POST'])
def employees_collection(request):
    if request.method == 'GET':
        raw_status = str(request.query_params.get('status', 'all')).strip().lower()
        search_term = str(request.query_params.get('search', '')).strip()

        try:
            limit = int(request.query_params.get('limit', 25))
            offset = int(request.query_params.get('offset', 0))
        except (TypeError, ValueError):
            return _api_error(message='limit and offset must be valid integers.')

        if raw_status not in {'all', 'active', 'exited'}:
            return _api_error(message='status must be one of: all, active, exited.')
        if limit < 1 or limit > 200:
            return _api_error(message='limit must be between 1 and 200.')
        if offset < 0:
            return _api_error(message='offset cannot be negative.')

        like_value = f'%{search_term}%'
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT emp_id, first_name, middle_name, last_name, start_date, end_date
                FROM emp_master
                WHERE (
                    %s = 'all'
                    OR (%s = 'active' AND end_date IS NULL)
                    OR (%s = 'exited' AND end_date IS NOT NULL)
                )
                AND (
                    %s = ''
                    OR CAST(emp_id AS CHAR) LIKE %s
                    OR CONCAT_WS(' ', first_name, middle_name, last_name) LIKE %s
                )
                ORDER BY emp_id DESC
                LIMIT %s OFFSET %s
                ''',
                [raw_status, raw_status, raw_status, search_term, like_value, like_value, limit, offset],
            )
            rows = cursor.fetchall()

        employees = [_row_to_employee(row) for row in rows]
        data = {
            'items': employees,
            'pagination': {'limit': limit, 'offset': offset, 'returned': len(employees)},
            'counts': _employee_counts(),
        }
        return _api_success(data=data, message='Employee records fetched.')

    payload = request.data or {}
    errors: dict[str, str] = {}

    try:
        emp_id = int(payload.get('emp_id'))
    except (TypeError, ValueError):
        errors['emp_id'] = 'emp_id is required and must be a positive integer.'
        emp_id = None

    if emp_id is not None and emp_id <= 0:
        errors['emp_id'] = 'emp_id must be a positive integer.'

    first_name = _normalize_name(payload.get('first_name'))
    middle_name = _normalize_name(payload.get('middle_name')) or None
    last_name = _normalize_name(payload.get('last_name'))
    start_date, start_date_error = _parse_employee_date(payload.get('start_date'), field='start_date')
    end_date, end_date_error = _parse_employee_date(payload.get('end_date'), field='end_date', required=False)

    if not first_name:
        errors['first_name'] = 'first_name is required.'
    if not last_name:
        errors['last_name'] = 'last_name is required.'
    if start_date_error:
        errors['start_date'] = start_date_error
    if end_date_error:
        errors['end_date'] = end_date_error

    if first_name and len(first_name) > 50:
        errors['first_name'] = 'first_name cannot exceed 50 characters.'
    if middle_name and len(middle_name) > 50:
        errors['middle_name'] = 'middle_name cannot exceed 50 characters.'
    if last_name and len(last_name) > 50:
        errors['last_name'] = 'last_name cannot exceed 50 characters.'

    if start_date and end_date and end_date < start_date:
        errors['end_date'] = 'end_date must be greater than or equal to start_date.'

    if errors:
        return _api_error(message='Validation failed.', errors=errors)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM emp_master WHERE emp_id = %s FOR UPDATE', [emp_id])
                if cursor.fetchone():
                    return _api_error(
                        message=f'Employee ID {emp_id} already exists.',
                        status_code=status.HTTP_409_CONFLICT,
                    )

                cursor.execute(
                    '''
                    INSERT INTO emp_master (emp_id, first_name, middle_name, last_name, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ''',
                    [emp_id, first_name, middle_name, last_name, start_date, end_date],
                )

                row = _fetch_employee_row(emp_id, cursor=cursor)
    except IntegrityError:
        return _api_error(
            message='Unable to create employee due to database constraints.',
            status_code=status.HTTP_409_CONFLICT,
        )

    return _api_success(
        message='Employee created successfully.',
        status_code=status.HTTP_201_CREATED,
        data=_row_to_employee(row),
    )


@api_view(['GET', 'PUT'])
def employee_item(request, emp_id: int):
    if request.method == 'GET':
        row = _fetch_employee_row(emp_id)
        if row is None:
            return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)
        return _api_success(message='Employee fetched.', data=_row_to_employee(row))

    row = _fetch_employee_row(emp_id)
    if row is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    payload = request.data or {}
    errors: dict[str, str] = {}
    existing_employee = _row_to_employee(row)

    first_name = _normalize_name(payload.get('first_name'))
    middle_name = _normalize_name(payload.get('middle_name')) or None
    last_name = _normalize_name(payload.get('last_name'))
    start_date, start_date_error = _parse_employee_date(payload.get('start_date'), field='start_date')

    if not first_name:
        errors['first_name'] = 'first_name is required.'
    if not last_name:
        errors['last_name'] = 'last_name is required.'
    if start_date_error:
        errors['start_date'] = start_date_error

    if first_name and len(first_name) > 50:
        errors['first_name'] = 'first_name cannot exceed 50 characters.'
    if middle_name and len(middle_name) > 50:
        errors['middle_name'] = 'middle_name cannot exceed 50 characters.'
    if last_name and len(last_name) > 50:
        errors['last_name'] = 'last_name cannot exceed 50 characters.'

    existing_end_date = row[5]
    if start_date and existing_end_date and start_date > existing_end_date:
        errors['start_date'] = 'start_date cannot be after current end_date.'

    if errors:
        return _api_error(message='Validation failed.', errors=errors)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                UPDATE emp_master
                SET first_name = %s,
                    middle_name = %s,
                    last_name = %s,
                    start_date = %s
                WHERE emp_id = %s
                ''',
                [first_name, middle_name, last_name, start_date, emp_id],
            )
            updated_row = _fetch_employee_row(emp_id, cursor=cursor)

    if updated_row is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    changed = [
        field_name
        for field_name in ('first_name', 'middle_name', 'last_name', 'start_date')
        if existing_employee.get(field_name) != _row_to_employee(updated_row).get(field_name)
    ]
    message = 'Employee updated successfully.'
    if changed:
        message = f'Employee updated successfully. Changed: {", ".join(changed)}.'

    return _api_success(message=message, data=_row_to_employee(updated_row))


@api_view(['POST'])
def employee_exit(request, emp_id: int):
    row = _fetch_employee_row(emp_id)
    if row is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    if row[5] is not None:
        return _api_error(
            message=f'Employee {emp_id} is already exited.',
            status_code=status.HTTP_409_CONFLICT,
        )

    payload = request.data or {}
    end_date, end_date_error = _parse_employee_date(payload.get('end_date'), field='end_date')
    if end_date_error:
        return _api_error(message='Validation failed.', errors={'end_date': end_date_error})

    if end_date is not None and end_date < row[4]:
        return _api_error(
            message='Validation failed.',
            errors={'end_date': 'end_date must be greater than or equal to start_date.'},
        )

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('UPDATE emp_master SET end_date = %s WHERE emp_id = %s', [end_date, emp_id])
            updated_row = _fetch_employee_row(emp_id, cursor=cursor)

    return _api_success(message='Employee deactivated successfully.', data=_row_to_employee(updated_row))


@api_view(['GET'])
def employee_profile(request, emp_id: int):
    profile = _employee_profile_data(emp_id)
    if profile is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    return _api_success(message='Employee profile fetched.', data=profile)


REQUIRED_ONBOARDING_DOCS = [
    {
        'key': 'aadhaar',
        'label': 'Aadhar',
        'comp_type': 'Aadhaar Verification',
        'reg_field': 'aadhaar',
        'aliases': {'aadhaar', 'aadhar', 'onboarding.gov_id'},
    },
    {
        'key': 'pan',
        'label': 'PAN',
        'comp_type': 'PAN Verification',
        'reg_field': 'pan',
        'aliases': {'pan'},
    },
    {
        'key': 'uan',
        'label': 'UAN',
        'comp_type': 'UAN Linking',
        'reg_field': 'uan_epf_acctno',
        'aliases': {'uan', 'epf', 'uan_epf_acctno'},
    },
]

ALLOWED_DOC_STATUSES = {'pending', 'verified', 'rejected', 'missing'}


def _next_uint_id(cursor, *, table: str, id_col: str) -> int:
    cursor.execute(f'SELECT COALESCE(MAX({id_col}), 0) + 1 FROM {table}')
    return int(cursor.fetchone()[0])


def _normalize_tracker_status(raw_status: object) -> str:
    value = str(raw_status or '').strip().lower()
    if value in {'verified', 'approve', 'approved', 'complete', 'completed'}:
        return 'verified'
    if value in {'pending', 'in_progress', 'in progress', 'awaiting'}:
        return 'pending'
    if value in {'rejected', 'failed', 'declined'}:
        return 'rejected'
    if value in {'missing', 'not_uploaded', 'not uploaded', 'na', 'n/a'}:
        return 'missing'
    return value or 'missing'


def _doc_definition_by_key(doc_key: str) -> dict | None:
    key = str(doc_key or '').strip().lower()
    if not key:
        return None

    for item in REQUIRED_ONBOARDING_DOCS:
        if key == str(item['key']).lower():
            return item
        if key == str(item['comp_type']).lower():
            return item
        if key in item.get('aliases', set()):
            return item

    if 'aadhaar' in key or 'aadhar' in key:
        return next((item for item in REQUIRED_ONBOARDING_DOCS if item['key'] == 'aadhaar'), None)
    if re.search(r'(^|\W)pan(\W|$)', key):
        return next((item for item in REQUIRED_ONBOARDING_DOCS if item['key'] == 'pan'), None)
    if 'uan' in key:
        return next((item for item in REQUIRED_ONBOARDING_DOCS if item['key'] == 'uan'), None)
    return None


def _comp_type_for_key(doc_key: str) -> str:
    definition = _doc_definition_by_key(doc_key)
    if definition is None:
        return str(doc_key or '').strip()
    return str(definition['comp_type'])


def _required_doc_types() -> list[str]:
    return [item['comp_type'] for item in REQUIRED_ONBOARDING_DOCS]


def _pagination_values(request, *, default_limit: int = 10, max_limit: int = 200) -> tuple[int | None, int | None, Response | None]:
    try:
        limit = int(request.query_params.get('limit', default_limit))
        offset = int(request.query_params.get('offset', 0))
    except (TypeError, ValueError):
        return None, None, _api_error(message='limit and offset must be valid integers.')

    if limit < 1 or limit > max_limit:
        return None, None, _api_error(message=f'limit must be between 1 and {max_limit}.')
    if offset < 0:
        return None, None, _api_error(message='offset cannot be negative.')
    return limit, offset, None


def _paginated_payload(items: list[dict], *, limit: int, offset: int, total: int) -> dict[str, int]:
    returned = len(items)
    return {
        'limit': limit,
        'offset': offset,
        'returned': returned,
        'total': total,
        'has_more': int(offset + returned < total),
    }

def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_label(value: date) -> str:
    return f'{value.year:04d}-{value.month:02d}'


def _parse_month(value: str) -> date | None:
    raw = (value or '').strip()
    if not raw:
        return None
    if len(raw) != 7 or raw[4] != '-':
        return None
    try:
        y = int(raw[:4])
        m = int(raw[5:])
        return date(y, m, 1)
    except ValueError:
        return None


def _documents_for_employee(emp_id: int) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT emp_compliance_tracker_id, comp_type, status, doc_url
            FROM emp_compliance_tracker
            WHERE emp_id = %s
            ORDER BY emp_compliance_tracker_id DESC
            ''',
            [emp_id],
        )
        rows = cursor.fetchall()

    return [
        {
            'id': int(row[0]),
            'comp_type': row[1],
            'status': _normalize_tracker_status(row[2]),
            'doc_url': row[3],
        }
        for row in rows
    ]


def _latest_tracker_by_key_for_employee(emp_id: int) -> dict[str, dict[str, object]]:
    documents = _documents_for_employee(emp_id)
    latest_by_key: dict[str, dict[str, object]] = {}
    for doc in documents:
        definition = _doc_definition_by_key(str(doc.get('comp_type') or ''))
        if definition is None:
            continue
        key = str(definition['key'])
        if key not in latest_by_key:
            latest_by_key[key] = doc
    return latest_by_key


def _registration_snapshot(emp_id: int) -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT pan, aadhaar, uan_epf_acctno
            FROM emp_reg_info
            WHERE emp_id = %s
            LIMIT 1
            ''',
            [emp_id],
        )
        row = cursor.fetchone()
    if row is None:
        return {'pan': '', 'aadhaar': '', 'uan_epf_acctno': ''}
    return {
        'pan': str(row[0] or '').strip(),
        'aadhaar': str(row[1] or '').strip(),
        'uan_epf_acctno': str(row[2] or '').strip(),
    }


def _onboarding_snapshot(emp_id: int) -> dict[str, object]:
    docs = _documents_for_employee(emp_id)
    latest_by_key = _latest_tracker_by_key_for_employee(emp_id)
    registration_values = _registration_snapshot(emp_id)

    checklist = []
    completed = 0
    for item in REQUIRED_ONBOARDING_DOCS:
        key = str(item['key'])
        reg_field = str(item['reg_field'])
        reg_value = str(registration_values.get(reg_field) or '').strip()
        tracker_doc = latest_by_key.get(key)
        document_exists = bool(reg_value) or tracker_doc is not None
        checklist_status = 'verified' if document_exists else 'missing'
        if checklist_status == 'verified':
            completed += 1
        checklist.append(
            {
                'key': key,
                'label': item['label'],
                'comp_type': item['comp_type'],
                'status': checklist_status,
                'completed': checklist_status == 'verified',
                'document_id': tracker_doc['id'] if tracker_doc else None,
                'doc_url': tracker_doc['doc_url'] if tracker_doc else '',
            }
        )

    total = len(REQUIRED_ONBOARDING_DOCS)
    completion_percent = round((completed / total) * 100, 2) if total else 0.0
    return {
        'checklist': checklist,
        'documents': docs,
        'summary': {
            'total_items': total,
            'completed_items': completed,
            'pending_items': total - completed,
            'completion_percent': completion_percent,
        },
    }


@api_view(['GET'])
def employee_onboarding_status(request, emp_id: int):
    row = _fetch_employee_row(emp_id)
    if row is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    snapshot = _onboarding_snapshot(emp_id)
    return _api_success(
        message='Onboarding checklist fetched.',
        data={
            'emp_id': emp_id,
            'employee_name': _row_to_employee(row).get('full_name'),
            **snapshot,
        },
    )


@api_view(['POST'])
def employee_document_add(request, emp_id: int):
    if _fetch_employee_row(emp_id) is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    payload = request.data or {}
    comp_type = _comp_type_for_key(str(payload.get('comp_type') or payload.get('key') or payload.get('type') or '').strip())
    status_value = _normalize_tracker_status(payload.get('status') or 'pending')
    doc_url = str(payload.get('doc_url') or '').strip()

    errors: dict[str, str] = {}
    if not comp_type:
        errors['comp_type'] = 'comp_type is required.'
    if status_value not in ALLOWED_DOC_STATUSES:
        errors['status'] = f"status must be one of: {', '.join(sorted(ALLOWED_DOC_STATUSES))}."
    if not doc_url:
        errors['doc_url'] = 'doc_url is required.'
    if errors:
        return _api_error(message='Validation failed.', errors=errors)

    with transaction.atomic():
        with connection.cursor() as cursor:
            doc_id = _next_uint_id(cursor, table='emp_compliance_tracker', id_col='emp_compliance_tracker_id')
            cursor.execute(
                '''
                INSERT INTO emp_compliance_tracker (emp_compliance_tracker_id, emp_id, comp_type, status, doc_url)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                [doc_id, emp_id, comp_type, status_value.capitalize(), doc_url],
            )

    return _api_success(
        message='Document record added.',
        status_code=status.HTTP_201_CREATED,
        data={
            'id': doc_id,
            'emp_id': emp_id,
            'comp_type': comp_type,
            'status': _normalize_tracker_status(status_value),
            'doc_url': doc_url,
        },
    )


@api_view(['PUT', 'PATCH'])
def employee_document_update(request, emp_id: int, doc_id: int):
    payload = request.data or {}
    next_status = payload.get('status')
    next_url = payload.get('doc_url')

    updates: list[str] = []
    params: list[object] = []
    errors: dict[str, str] = {}

    if next_status is not None:
        status_value = _normalize_tracker_status(next_status)
        if status_value not in ALLOWED_DOC_STATUSES:
            errors['status'] = f"status must be one of: {', '.join(sorted(ALLOWED_DOC_STATUSES))}."
        else:
            updates.append('status = %s')
            params.append(status_value.capitalize())

    if next_url is not None:
        url_value = str(next_url).strip()
        if not url_value:
            errors['doc_url'] = 'doc_url cannot be empty.'
        else:
            updates.append('doc_url = %s')
            params.append(url_value)

    if errors:
        return _api_error(message='Validation failed.', errors=errors)
    if not updates:
        return _api_error(message='No fields to update.')

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT emp_compliance_tracker_id
                FROM emp_compliance_tracker
                WHERE emp_compliance_tracker_id = %s AND emp_id = %s
                ''',
                [doc_id, emp_id],
            )
            if cursor.fetchone() is None:
                return _api_error(message='Document record not found.', status_code=status.HTTP_404_NOT_FOUND)

            query = f"UPDATE emp_compliance_tracker SET {', '.join(updates)} WHERE emp_compliance_tracker_id = %s AND emp_id = %s"
            cursor.execute(query, [*params, doc_id, emp_id])

            cursor.execute(
                '''
                SELECT emp_compliance_tracker_id, emp_id, comp_type, status, doc_url
                FROM emp_compliance_tracker
                WHERE emp_compliance_tracker_id = %s
                ''',
                [doc_id],
            )
            row = cursor.fetchone()

    return _api_success(
        message='Document status updated.',
        data={
            'id': int(row[0]),
            'emp_id': int(row[1]),
            'comp_type': row[2],
            'status': _normalize_tracker_status(row[3]),
            'doc_url': row[4],
        },
    )


@api_view(['GET'])
def onboarding_progress(request):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT emp_id, first_name, middle_name, last_name
            FROM emp_master
            ORDER BY emp_id ASC
            ''',
        )
        employees = cursor.fetchall()

        cursor.execute(
            '''
            SELECT emp_id, pan, aadhaar, uan_epf_acctno
            FROM emp_reg_info
            '''
        )
        reg_rows = cursor.fetchall()

        cursor.execute(
            '''
            SELECT emp_compliance_tracker_id, emp_id, comp_type, status
            FROM emp_compliance_tracker
            ORDER BY emp_compliance_tracker_id DESC
            '''
        )
        tracker_rows = cursor.fetchall()

    reg_map = {
        int(row[0]): {
            'pan': str(row[1] or '').strip(),
            'aadhaar': str(row[2] or '').strip(),
            'uan_epf_acctno': str(row[3] or '').strip(),
        }
        for row in reg_rows
    }

    latest_tracker_by_key: dict[tuple[int, str], str] = {}
    for _, emp_id, comp_type, status_value in tracker_rows:
        definition = _doc_definition_by_key(str(comp_type or ''))
        if definition is None:
            continue
        map_key = (int(emp_id), str(definition['key']))
        if map_key not in latest_tracker_by_key:
            latest_tracker_by_key[map_key] = _normalize_tracker_status(status_value)

    total_items = len(REQUIRED_ONBOARDING_DOCS)
    completed_count = 0
    in_progress_count = 0
    not_started_count = 0
    progress_rows = []

    for emp_id, first, middle, last in employees:
        emp_id_int = int(emp_id)
        full_name = ' '.join(part for part in [first, middle, last] if part)
        completed = 0
        touched = 0
        reg_snapshot = reg_map.get(emp_id_int, {})
        for definition in REQUIRED_ONBOARDING_DOCS:
            key = str(definition['key'])
            reg_field = str(definition['reg_field'])
            tracker_status = latest_tracker_by_key.get((emp_id_int, key), 'missing')
            reg_exists = bool(str(reg_snapshot.get(reg_field) or '').strip())
            exists = reg_exists or tracker_status != 'missing'
            if exists:
                touched += 1
                completed += 1

        pct = round((completed / total_items) * 100, 2) if total_items else 0.0
        if completed == total_items:
            completed_count += 1
            phase = 'completed'
        elif touched == 0:
            not_started_count += 1
            phase = 'not_started'
        else:
            in_progress_count += 1
            phase = 'in_progress'

        progress_rows.append(
            {
                'emp_id': emp_id_int,
                'employee_name': full_name,
                'completed_items': completed,
                'total_items': total_items,
                'completion_percent': pct,
                'phase': phase,
            }
        )

    return _api_success(
        message='Onboarding progress fetched.',
        data={
            'metrics': {
                'total_employees': len(employees),
                'completed': completed_count,
                'in_progress': in_progress_count,
                'not_started': not_started_count,
            },
            'employees': progress_rows,
        },
    )


@api_view(['GET', 'POST'])
def employee_ctc_history(request, emp_id: int):
    if _fetch_employee_row(emp_id) is None:
        return _api_error(message=f'Employee {emp_id} not found.', status_code=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT emp_ctc_id, int_title, ext_title, main_level, sub_level, start_of_ctc, end_of_ctc, ctc_amt
                FROM emp_ctc_info
                WHERE emp_id = %s
                ORDER BY start_of_ctc DESC, emp_ctc_id DESC
                ''',
                [emp_id],
            )
            rows = cursor.fetchall()

        timeline = [
            {
                'emp_ctc_id': int(row[0]),
                'int_title': row[1],
                'ext_title': row[2],
                'main_level': int(row[3]),
                'sub_level': row[4],
                'start_of_ctc': row[5].isoformat() if row[5] else None,
                'end_of_ctc': row[6].isoformat() if row[6] else None,
                'ctc_amt': int(row[7]),
            }
            for row in rows
        ]
        return _api_success(message='CTC timeline fetched.', data={'emp_id': emp_id, 'timeline': timeline})

    payload = request.data or {}
    int_title = str(payload.get('int_title') or '').strip()
    ext_title = str(payload.get('ext_title') or '').strip()
    sub_level = str(payload.get('sub_level') or '').strip().upper()
    start_of_ctc, start_error = _parse_employee_date(payload.get('start_of_ctc'), field='start_of_ctc')
    end_of_ctc, end_error = _parse_employee_date(payload.get('end_of_ctc'), field='end_of_ctc', required=False)

    errors: dict[str, str] = {}
    if not int_title:
        errors['int_title'] = 'int_title is required.'
    if not ext_title:
        errors['ext_title'] = 'ext_title is required.'
    if start_error:
        errors['start_of_ctc'] = start_error
    if end_error:
        errors['end_of_ctc'] = end_error
    if end_of_ctc and start_of_ctc and end_of_ctc < start_of_ctc:
        errors['end_of_ctc'] = 'end_of_ctc must be greater than or equal to start_of_ctc.'

    try:
        main_level = int(payload.get('main_level'))
    except (TypeError, ValueError):
        main_level = 0
        errors['main_level'] = 'main_level must be a positive integer.'
    if main_level <= 0:
        errors['main_level'] = 'main_level must be a positive integer.'

    try:
        ctc_amt = int(payload.get('ctc_amt'))
    except (TypeError, ValueError):
        ctc_amt = 0
        errors['ctc_amt'] = 'ctc_amt must be an integer.'
    if not (120000 <= ctc_amt <= 1200000):
        errors['ctc_amt'] = 'ctc_amt must be between 120000 and 1200000.'

    if len(sub_level) != 1:
        errors['sub_level'] = 'sub_level must be a single character.'

    if errors:
        return _api_error(message='Validation failed.', errors=errors)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT emp_ctc_id
                FROM emp_ctc_info
                WHERE emp_id = %s
                  AND (%s IS NULL OR start_of_ctc <= %s)
                  AND (end_of_ctc IS NULL OR end_of_ctc >= %s)
                LIMIT 1
                ''',
                [emp_id, end_of_ctc, end_of_ctc, start_of_ctc],
            )
            if cursor.fetchone() is not None:
                return _api_error(
                    message='Date range overlaps with an existing CTC record.',
                    status_code=status.HTTP_409_CONFLICT,
                )

            next_id = _next_uint_id(cursor, table='emp_ctc_info', id_col='emp_ctc_id')
            cursor.execute(
                '''
                INSERT INTO emp_ctc_info
                    (emp_ctc_id, emp_id, int_title, ext_title, main_level, sub_level, start_of_ctc, end_of_ctc, ctc_amt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                [next_id, emp_id, int_title, ext_title, main_level, sub_level, start_of_ctc, end_of_ctc, ctc_amt],
            )

    return _api_success(
        message='CTC/role change record added.',
        status_code=status.HTTP_201_CREATED,
        data={
            'emp_ctc_id': next_id,
            'emp_id': emp_id,
            'int_title': int_title,
            'ext_title': ext_title,
            'main_level': main_level,
            'sub_level': sub_level,
            'start_of_ctc': start_of_ctc.isoformat() if start_of_ctc else None,
            'end_of_ctc': end_of_ctc.isoformat() if end_of_ctc else None,
            'ctc_amt': ctc_amt,
        },
    )


def _build_compliance_dashboard_data() -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM emp_compliance_tracker')
        total_compliance_records = int(cursor.fetchone()[0] or 0)

        cursor.execute(
            '''
            SELECT emp_id, first_name, middle_name, last_name
            FROM emp_master
            ORDER BY emp_id ASC
            '''
        )
        employees = cursor.fetchall()

        cursor.execute(
            '''
            SELECT emp_id, pan, aadhaar, uan_epf_acctno
            FROM emp_reg_info
            '''
        )
        reg_rows = cursor.fetchall()

        cursor.execute(
            '''
            SELECT emp_compliance_tracker_id, emp_id, comp_type, status, doc_url
            FROM emp_compliance_tracker
            ORDER BY emp_compliance_tracker_id DESC
            '''
        )
        tracker_rows = cursor.fetchall()

    reg_map = {
        int(row[0]): {
            'pan': str(row[1] or '').strip(),
            'aadhaar': str(row[2] or '').strip(),
            'uan_epf_acctno': str(row[3] or '').strip(),
        }
        for row in reg_rows
    }

    latest_tracker_by_emp_key: dict[tuple[int, str], dict[str, object]] = {}
    for tracker_id, emp_id, comp_type, status_value, doc_url in tracker_rows:
        definition = _doc_definition_by_key(str(comp_type or ''))
        if definition is None:
            continue
        key = (int(emp_id), str(definition['key']))
        if key in latest_tracker_by_emp_key:
            continue
        latest_tracker_by_emp_key[key] = {
            'id': int(tracker_id),
            'comp_type': str(definition['comp_type']),
            'status': _normalize_tracker_status(status_value),
            'doc_url': str(doc_url or '').strip(),
        }

    employee_rows = []
    missing_total = 0
    pending_total = 0
    verified_total = 0
    employees_with_gaps = 0

    for emp_id, first, middle, last in employees:
        emp_id_int = int(emp_id)
        full_name = ' '.join(part for part in [first, middle, last] if part)
        reg_snapshot = reg_map.get(emp_id_int, {})

        document_status: dict[str, str] = {}
        missing_docs: list[str] = []
        pending_docs: list[str] = []
        verified_docs: list[str] = []

        for definition in REQUIRED_ONBOARDING_DOCS:
            doc_key = str(definition['key'])
            doc_label = str(definition['label'])
            reg_field = str(definition['reg_field'])
            reg_exists = bool(str(reg_snapshot.get(reg_field) or '').strip())

            tracker = latest_tracker_by_emp_key.get((emp_id_int, doc_key))
            tracker_status = str(tracker['status']) if tracker else 'missing'
            document_exists = reg_exists or tracker is not None

            if not document_exists:
                current_status = 'missing'
            elif tracker is None:
                current_status = 'verified'
            elif tracker_status in {'pending', 'rejected', 'missing'}:
                current_status = tracker_status
            else:
                current_status = 'verified'

            document_status[doc_key] = current_status

            if current_status == 'missing':
                missing_docs.append(doc_label)
            elif current_status == 'pending':
                pending_docs.append(doc_label)
            elif current_status == 'verified':
                verified_docs.append(doc_label)

        if missing_docs or pending_docs:
            employees_with_gaps += 1

        missing_total += len(missing_docs)
        pending_total += len(pending_docs)
        verified_total += len(verified_docs)

        completion_percent = round((len(verified_docs) / len(REQUIRED_ONBOARDING_DOCS)) * 100, 2) if REQUIRED_ONBOARDING_DOCS else 0.0
        employee_rows.append(
            {
                'emp_id': emp_id_int,
                'employee_name': full_name,
                'document_status': document_status,
                'missing_documents': missing_docs,
                'pending_documents': pending_docs,
                'verified_documents': verified_docs,
                'completion_percent': completion_percent,
            }
        )

    return {
        'metrics': {
            'total_employees': len(employees),
            'total_compliance_records': total_compliance_records,
            'missing_documents_count': missing_total,
            'pending_verification_count': pending_total,
            'verified_documents_count': verified_total,
            'employees_with_gaps': employees_with_gaps,
        },
        'employees': employee_rows,
    }


@api_view(['GET'])
def compliance_dashboard(request):
    limit, offset, pagination_error = _pagination_values(request, default_limit=10)
    if pagination_error is not None:
        return pagination_error

    return _api_success(
        message='Compliance dashboard fetched.',
        data={
            **(lambda source: {
                'metrics': source['metrics'],
                'employees': source['employees'][offset : offset + limit],
                'pagination': _paginated_payload(source['employees'][offset : offset + limit], limit=limit, offset=offset, total=len(source['employees'])),
            })(_build_compliance_dashboard_data()),
        },
    )


@api_view(['GET'])
def alerts_dashboard(request):
    limit, offset, pagination_error = _pagination_values(request, default_limit=15)
    if pagination_error is not None:
        return pagination_error

    dashboard_data = _build_compliance_dashboard_data()
    alerts = []
    alert_id = 1
    for row in dashboard_data['employees']:
        emp_id = row['emp_id']
        name = row['employee_name']
        for comp_type in row.get('missing_documents', []):
            alerts.append(
                {
                    'alert_id': alert_id,
                    'emp_id': emp_id,
                    'employee_name': name,
                    'type': 'missing_document',
                    'severity': 'high',
                    'status': 'open',
                    'message': f'Missing compliance document: {comp_type}',
                }
            )
            alert_id += 1
        for comp_type in row.get('pending_documents', []):
            alerts.append(
                {
                    'alert_id': alert_id,
                    'emp_id': emp_id,
                    'employee_name': name,
                    'type': 'pending_verification',
                    'severity': 'medium',
                    'status': 'open',
                    'message': f'Pending verification: {comp_type}',
                }
            )
            alert_id += 1

    paged_alerts = alerts[offset : offset + limit]

    return _api_success(
        message='Alerts fetched.',
        data={
            'metrics': {
                'total_alerts': len(alerts),
                'high_severity': len([a for a in alerts if a['severity'] == 'high']),
                'medium_severity': len([a for a in alerts if a['severity'] == 'medium']),
            },
            'alerts': paged_alerts,
            'pagination': _paginated_payload(paged_alerts, limit=limit, offset=offset, total=len(alerts)),
        },
    )


@api_view(['GET'])
def report_headcount(request):
    return _api_success(message='Headcount report fetched.', data={'counts': _employee_counts()})


@api_view(['GET'])
def report_joiners_leavers(request):
    start_month = _parse_month(str(request.query_params.get('start_month') or ''))
    end_month = _parse_month(str(request.query_params.get('end_month') or ''))

    if start_month is None or end_month is None:
        today = date.today()
        end_month = _month_start(today)
        start_month = end_month
        for _ in range(2):
            previous_month_end = start_month - timedelta(days=1)
            start_month = date(previous_month_end.year, previous_month_end.month, 1)

    if start_month > end_month:
        return _api_error(message='start_month must be earlier than or equal to end_month.')

    range_start = start_month
    range_end = _next_month(end_month)

    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT start_date, end_date
            FROM emp_master
            WHERE start_date < %s
               OR (end_date IS NOT NULL AND end_date < %s)
            ''',
            [range_end, range_end],
        )
        rows = cursor.fetchall()

    joiners_map: dict[str, int] = {}
    leavers_map: dict[str, int] = {}

    for start_dt, end_dt in rows:
        if start_dt and range_start <= start_dt < range_end:
            key = _month_label(_month_start(start_dt))
            joiners_map[key] = joiners_map.get(key, 0) + 1
        if end_dt and range_start <= end_dt < range_end:
            key = _month_label(_month_start(end_dt))
            leavers_map[key] = leavers_map.get(key, 0) + 1

    buckets = []
    cursor_month = start_month
    while cursor_month <= end_month:
        key = _month_label(cursor_month)
        buckets.append(
            {
                'month': key,
                'joiners': joiners_map.get(key, 0),
                'leavers': leavers_map.get(key, 0),
            }
        )
        cursor_month = _next_month(cursor_month)

    return _api_success(message='Joiners and leavers report fetched.', data={'months': buckets})


@api_view(['GET'])
def report_ctc_level_distribution(request):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT c.emp_id, c.main_level, c.ctc_amt
            FROM emp_ctc_info c
            JOIN (
                SELECT emp_id, MAX(emp_ctc_id) AS latest_id
                FROM emp_ctc_info
                GROUP BY emp_id
            ) latest
            ON latest.emp_id = c.emp_id AND latest.latest_id = c.emp_ctc_id
            '''
        )
        rows = cursor.fetchall()

    bands = [
        {'label': '120k-300k', 'min': 120000, 'max': 300000},
        {'label': '300k-600k', 'min': 300001, 'max': 600000},
        {'label': '600k-900k', 'min': 600001, 'max': 900000},
        {'label': '900k-1200k', 'min': 900001, 'max': 1200000},
    ]
    band_counts = {band['label']: 0 for band in bands}
    level_counts: dict[str, int] = {}

    for _, level, ctc_amt in rows:
        amount = int(ctc_amt)
        for band in bands:
            if band['min'] <= amount <= band['max']:
                band_counts[band['label']] += 1
                break
        level_key = str(int(level))
        level_counts[level_key] = level_counts.get(level_key, 0) + 1

    return _api_success(
        message='CTC and level distribution fetched.',
        data={
            'salary_bands': [{'band': key, 'count': value} for key, value in band_counts.items()],
            'level_counts': [{'level': key, 'count': value} for key, value in sorted(level_counts.items(), key=lambda x: int(x[0]))],
        },
    )


@api_view(['GET'])
def report_compliance_status(request):
    status_filter_raw = str(request.query_params.get('status') or '').strip().lower()
    status_filter = '' if status_filter_raw in {'', 'all'} else _normalize_tracker_status(status_filter_raw)

    type_filter_raw = str(request.query_params.get('type') or '').strip()
    type_filter = '' if not type_filter_raw or type_filter_raw.lower() == 'all' else _comp_type_for_key(type_filter_raw)

    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT
                t.emp_compliance_tracker_id,
                t.emp_id,
                CONCAT_WS(' ', m.first_name, m.middle_name, m.last_name) AS full_name,
                t.comp_type,
                t.status,
                t.doc_url
            FROM emp_compliance_tracker t
            JOIN emp_master m ON m.emp_id = t.emp_id
            ORDER BY t.emp_id ASC, t.emp_compliance_tracker_id DESC
            '''
        )
        rows = cursor.fetchall()

    items = []
    counts_by_status: dict[str, int] = {}
    counts_by_type: dict[str, int] = {}
    for row in rows:
        status_value = _normalize_tracker_status(row[4])
        if status_filter and status_value != status_filter:
            continue

        definition = _doc_definition_by_key(str(row[3] or ''))
        type_value = str(definition['comp_type']) if definition is not None else str(row[3] or '').strip()
        if type_filter and type_value != type_filter:
            continue

        counts_by_status[status_value] = counts_by_status.get(status_value, 0) + 1
        counts_by_type[type_value] = counts_by_type.get(type_value, 0) + 1
        items.append(
            {
                'document_id': int(row[0]),
                'emp_id': int(row[1]),
                'employee_name': row[2],
                'comp_type': type_value,
                'status': status_value,
                'doc_url': row[5],
            }
        )

    return _api_success(
        message='Compliance status report fetched.',
        data={
            'filters': {'status': status_filter or 'all', 'type': type_filter or 'all'},
            'summary': {
                'total_records': len(items),
                'pending': counts_by_status.get('pending', 0),
                'verified': counts_by_status.get('verified', 0),
                'non_compliant': counts_by_status.get('missing', 0) + counts_by_status.get('rejected', 0),
            },
            'counts_by_status': counts_by_status,
            'counts_by_type': counts_by_type,
            'items': items,
        },
    )
