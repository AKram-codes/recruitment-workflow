import json

from django.db import connection
from django.test import Client


client = Client()
results: list[tuple[str, bool, str]] = []


def add_result(name: str, ok: bool, detail: str = '') -> None:
    results.append((name, bool(ok), detail))


def parse_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def jpost(path: str, payload: dict):
    return client.post(path, data=json.dumps(payload), content_type='application/json')


def jpatch(path: str, payload: dict):
    return client.patch(path, data=json.dumps(payload), content_type='application/json')


with connection.cursor() as cur:
    cur.execute('SELECT COALESCE(MAX(emp_id), 0) + 1 FROM emp_master')
    temp_emp_id = int(cur.fetchone()[0])


create_payload = {
    'emp_id': temp_emp_id,
    'first_name': 'Temp',
    'middle_name': 'Audit',
    'last_name': 'User',
    'start_date': '2024-01-15',
}
create_response = jpost('/api/employees', create_payload)
create_json = parse_json(create_response)
add_result(
    'bootstrap temporary employee created',
    create_response.status_code == 201,
    f'status={create_response.status_code} body={create_json}',
)

# 1) Onboarding checklist + docs
onb_before_resp = client.get(f'/api/employees/{temp_emp_id}/onboarding')
onb_before_json = parse_json(onb_before_resp).get('data', {})
checklist_before = onb_before_json.get('checklist') or []
add_result(
    'onboarding checklist visible per employee',
    onb_before_resp.status_code == 200 and isinstance(checklist_before, list),
    f'status={onb_before_resp.status_code}',
)
add_result(
    'onboarding tracks at least 3 checklist items',
    len(checklist_before) >= 3,
    f'count={len(checklist_before)}',
)

doc_specs = [
    ('gov_id', 'https://example.com/docs/gov-id.pdf'),
    ('address_proof', 'https://example.com/docs/address-proof.pdf'),
    ('signed_offer_letter', 'https://example.com/docs/signed-offer.pdf'),
]
doc_ids: dict[str, int] = {}
for key, url in doc_specs:
    resp = jpost(f'/api/employees/{temp_emp_id}/documents', {'key': key, 'status': 'pending', 'doc_url': url})
    data = parse_json(resp).get('data', {})
    add_result(
        f'document add works for {key}',
        resp.status_code == 201,
        f'status={resp.status_code} data={data}',
    )
    if data.get('id') is not None:
        doc_ids[key] = int(data['id'])

onb_after_add = parse_json(client.get(f'/api/employees/{temp_emp_id}/onboarding')).get('data', {})
status_map_after_add = {item.get('key'): item.get('status') for item in onb_after_add.get('checklist') or []}
add_result(
    'onboarding status updates after document add',
    all(status_map_after_add.get(key) in {'pending', 'verified', 'rejected'} for key, _ in doc_specs),
    str(status_map_after_add),
)

if 'gov_id' in doc_ids:
    verify_resp = jpatch(f"/api/employees/{temp_emp_id}/documents/{doc_ids['gov_id']}", {'status': 'verified'})
    add_result('document status endpoint updates to verified', verify_resp.status_code == 200, f'status={verify_resp.status_code}')
else:
    add_result('document status endpoint updates to verified', False, 'gov_id record missing')

onb_after_verify = parse_json(client.get(f'/api/employees/{temp_emp_id}/onboarding')).get('data', {})
summary_after_verify = onb_after_verify.get('summary') or {}
add_result(
    'onboarding completion % visible',
    isinstance(summary_after_verify.get('completion_percent'), (int, float)),
    str(summary_after_verify),
)
add_result(
    'onboarding completion % increases after verification',
    (summary_after_verify.get('completion_percent') or 0) > 0,
    str(summary_after_verify),
)

onb_progress_resp = client.get('/api/onboarding/progress')
onb_progress_data = parse_json(onb_progress_resp).get('data', {})
progress_rows = onb_progress_data.get('employees') or []
add_result(
    'HR onboarding progress view works',
    onb_progress_resp.status_code == 200 and any(int(row.get('emp_id')) == temp_emp_id for row in progress_rows),
    f'status={onb_progress_resp.status_code}',
)

# 2) Job/Role changes + overlap prevention + timeline
ctc_first = {
    'int_title': 'Software Engineer I',
    'ext_title': 'Engineer I',
    'main_level': 3,
    'sub_level': 'A',
    'start_of_ctc': '2024-01-15',
    'end_of_ctc': '2024-12-31',
    'ctc_amt': 450000,
}
ctc_second = {
    'int_title': 'Software Engineer II',
    'ext_title': 'Engineer II',
    'main_level': 4,
    'sub_level': 'B',
    'start_of_ctc': '2025-01-01',
    'end_of_ctc': None,
    'ctc_amt': 700000,
}
ctc_one_resp = jpost(f'/api/employees/{temp_emp_id}/ctc-history', ctc_first)
ctc_two_resp = jpost(f'/api/employees/{temp_emp_id}/ctc-history', ctc_second)
add_result('ctc record 1 added', ctc_one_resp.status_code == 201, f'status={ctc_one_resp.status_code}')
add_result('ctc record 2 added', ctc_two_resp.status_code == 201, f'status={ctc_two_resp.status_code}')

ctc_overlap = {
    'int_title': 'Overlap',
    'ext_title': 'Overlap',
    'main_level': 4,
    'sub_level': 'C',
    'start_of_ctc': '2024-06-01',
    'end_of_ctc': '2024-06-30',
    'ctc_amt': 500000,
}
ctc_overlap_resp = jpost(f'/api/employees/{temp_emp_id}/ctc-history', ctc_overlap)
add_result(
    'ctc overlapping date entries are rejected',
    ctc_overlap_resp.status_code == 409,
    f'status={ctc_overlap_resp.status_code} body={parse_json(ctc_overlap_resp)}',
)

ctc_timeline_resp = client.get(f'/api/employees/{temp_emp_id}/ctc-history')
ctc_timeline = parse_json(ctc_timeline_resp).get('data', {}).get('timeline') or []
add_result('ctc timeline view available', ctc_timeline_resp.status_code == 200, f'status={ctc_timeline_resp.status_code}')
add_result('ctc timeline has 2+ entries', len(ctc_timeline) >= 2, f'len={len(ctc_timeline)}')
add_result(
    'ctc records stored with expected dates',
    any(row.get('start_of_ctc') == '2024-01-15' for row in ctc_timeline)
    and any(row.get('start_of_ctc') == '2025-01-01' for row in ctc_timeline),
    str(ctc_timeline[:3]),
)

# 3) Exit workflow + 7) headcount update
head_before = parse_json(client.get('/api/reports/headcount')).get('data', {}).get('counts', {})
exit_resp = jpost(f'/api/employees/{temp_emp_id}/exit', {'end_date': '2024-02-20'})
add_result('exit date captured by API', exit_resp.status_code == 200, f'status={exit_resp.status_code}')

with connection.cursor() as cur:
    cur.execute('SELECT end_date FROM emp_master WHERE emp_id = %s', [temp_emp_id])
    db_row = cur.fetchone()
db_end_date = db_row[0].isoformat() if db_row and db_row[0] else None
add_result('employee marked inactive in DB', db_end_date == '2024-02-20', f'end_date={db_end_date}')

active_items = parse_json(client.get('/api/employees?status=active&limit=200&offset=0')).get('data', {}).get('items') or []
exited_items = parse_json(client.get('/api/employees?status=exited&limit=200&offset=0')).get('data', {}).get('items') or []
add_result(
    'exited employee removed from active directory',
    all(int(item.get('emp_id')) != temp_emp_id for item in active_items),
    f'active_count={len(active_items)}',
)
add_result(
    'exited employee appears in exited directory',
    any(int(item.get('emp_id')) == temp_emp_id for item in exited_items),
    f'exited_count={len(exited_items)}',
)

head_after = parse_json(client.get('/api/reports/headcount')).get('data', {}).get('counts', {})
add_result(
    'headcount realtime update active-1 after exit',
    head_after.get('active') == (head_before.get('active', 0) - 1),
    f'before={head_before} after={head_after}',
)
add_result(
    'headcount realtime update exited+1 after exit',
    head_after.get('exited') == (head_before.get('exited', 0) + 1),
    f'before={head_before} after={head_after}',
)
add_result(
    'headcount total unchanged after exit',
    head_after.get('total') == head_before.get('total'),
    f'before={head_before} after={head_after}',
)

# 4) Document verification list consistency
onb_doc_state = parse_json(client.get(f'/api/employees/{temp_emp_id}/onboarding')).get('data', {})
doc_list = onb_doc_state.get('documents') or []
add_result('document list per employee available', isinstance(doc_list, list) and len(doc_list) >= 3, f'len={len(doc_list)}')
add_result('document links stored as secure urls', any(str(item.get('doc_url', '')).startswith('https://') for item in doc_list), str(doc_list[:3]))

if 'address_proof' in doc_ids:
    upd = jpatch(f"/api/employees/{temp_emp_id}/documents/{doc_ids['address_proof']}", {'status': 'verified'})
    add_result('document status update pending->verified works', upd.status_code == 200, f'status={upd.status_code}')
    docs_after_upd = parse_json(client.get(f'/api/employees/{temp_emp_id}/onboarding')).get('data', {}).get('documents') or []
    target = [d for d in docs_after_upd if int(d.get('id')) == int(doc_ids['address_proof'])]
    add_result('document status reflected immediately in employee list', bool(target) and str(target[0].get('status')).lower() == 'verified', str(target))
else:
    add_result('document status update pending->verified works', False, 'address_proof doc id missing')
    add_result('document status reflected immediately in employee list', False, 'address_proof doc id missing')

# 5) Compliance dashboard checks
comp_resp = client.get('/api/compliance/dashboard')
comp_data = parse_json(comp_resp).get('data', {})
comp_metrics = comp_data.get('metrics') or {}
comp_rows = comp_data.get('employees') or []
add_result('compliance dashboard returns >=3 metrics', comp_resp.status_code == 200 and len(comp_metrics.keys()) >= 3, str(comp_metrics))
add_result('compliance dashboard employee list visible', isinstance(comp_rows, list), f'type={type(comp_rows).__name__}')

# 6) Alerts checks
alerts_before = parse_json(client.get('/api/alerts')).get('data', {}).get('alerts') or []
pending_before = [a for a in alerts_before if int(a.get('emp_id')) == temp_emp_id and str(a.get('type')) == 'pending_verification']
add_result('alerts generated for pending records', len(pending_before) >= 1, f'pending_before={len(pending_before)}')
add_result('alerts visible in API payload', isinstance(alerts_before, list), f'type={type(alerts_before).__name__}')

if 'signed_offer_letter' in doc_ids:
    _ = jpatch(f"/api/employees/{temp_emp_id}/documents/{doc_ids['signed_offer_letter']}", {'status': 'verified'})

alerts_after = parse_json(client.get('/api/alerts')).get('data', {}).get('alerts') or []
pending_after = [a for a in alerts_after if int(a.get('emp_id')) == temp_emp_id and str(a.get('type')) == 'pending_verification']
add_result('alerts reduce after verification update', len(pending_after) < len(pending_before), f'before={len(pending_before)} after={len(pending_after)}')

# 7) Headcount accuracy vs DB
with connection.cursor() as cur:
    cur.execute(
        '''
        SELECT
          COUNT(*) AS total_count,
          SUM(CASE WHEN end_date IS NULL THEN 1 ELSE 0 END) AS active_count,
          SUM(CASE WHEN end_date IS NOT NULL THEN 1 ELSE 0 END) AS exited_count
        FROM emp_master
        '''
    )
    total_count, active_count, exited_count = cur.fetchone()

head_api = parse_json(client.get('/api/reports/headcount')).get('data', {}).get('counts', {})
add_result('headcount total equals DB', int(head_api.get('total', -1)) == int(total_count or 0), f'api={head_api} db={(total_count, active_count, exited_count)}')
add_result('headcount active equals DB', int(head_api.get('active', -1)) == int(active_count or 0), f'api={head_api} db={(total_count, active_count, exited_count)}')
add_result('headcount exited equals DB', int(head_api.get('exited', -1)) == int(exited_count or 0), f'api={head_api} db={(total_count, active_count, exited_count)}')

# 8) Joiners/leavers report checks
jl_resp = client.get('/api/reports/joiners-leavers?start_month=2024-01&end_month=2024-03')
jl_rows = parse_json(jl_resp).get('data', {}).get('months') or []
jan = next((row for row in jl_rows if row.get('month') == '2024-01'), None)
feb = next((row for row in jl_rows if row.get('month') == '2024-02'), None)
add_result('joiners/leavers month grouping works', len(jl_rows) >= 3, str(jl_rows))
add_result('joiner count includes temp employee month', bool(jan) and int(jan.get('joiners', 0)) >= 1, str(jl_rows))
add_result('leaver count includes temp employee month', bool(feb) and int(feb.get('leavers', 0)) >= 1, str(jl_rows))

# 9) CTC & level distribution
dist_resp = client.get('/api/reports/ctc-level-distribution')
dist_data = parse_json(dist_resp).get('data', {})
salary_bands = dist_data.get('salary_bands') or []
level_counts = dist_data.get('level_counts') or []
add_result('ctc distribution has 3+ salary bands', len(salary_bands) >= 3, str(salary_bands))
add_result('ctc distribution has level-wise counts', len(level_counts) >= 1, str(level_counts))
add_result(
    'ctc distribution includes latest level from temp employee',
    any(str(item.get('level')) == '4' and int(item.get('count', 0)) >= 1 for item in level_counts),
    str(level_counts),
)

# 10) Compliance status report filters
status_report_all = parse_json(client.get('/api/reports/compliance-status')).get('data', {})
summary = status_report_all.get('summary') or {}
add_result(
    'compliance report shows pending/non-compliant',
    'pending' in summary and 'non_compliant' in summary,
    str(summary),
)

status_report_verified = parse_json(client.get('/api/reports/compliance-status?status=verified')).get('data', {})
verified_items = status_report_verified.get('items') or []
add_result(
    'compliance report filter by status works',
    all(str(item.get('status')).lower() == 'verified' for item in verified_items),
    str(verified_items[:5]),
)

status_report_type = parse_json(client.get('/api/reports/compliance-status?type=onboarding.gov_id')).get('data', {})
type_items = status_report_type.get('items') or []
add_result(
    'compliance report filter by type works',
    all(str(item.get('comp_type')) == 'onboarding.gov_id' for item in type_items),
    str(type_items[:5]),
)

passed = sum(1 for _, ok, _ in results if ok)
failed = len(results) - passed

print('AUDIT_TEMP_EMP_ID', temp_emp_id)
for name, ok, detail in results:
    print(('PASS' if ok else 'FAIL'), '|', name)
    if not ok:
        print('DETAIL:', detail)
print('AUDIT_SUMMARY', passed, len(results), failed)
