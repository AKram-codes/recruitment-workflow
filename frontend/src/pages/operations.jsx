import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiExitEmployee, apiListEmployees } from '../api/employeeApi.js'
import {
  apiAddCtcHistory,
  apiAddDocument,
  apiGetAlerts,
  apiGetComplianceDashboard,
  apiGetComplianceStatusReport,
  apiGetCtcHistory,
  apiGetCtcLevelDistribution,
  apiGetJoinersLeaversReport,
  apiGetOnboarding,
  apiGetOnboardingProgress,
  apiUpdateDocument,
} from '../api/opsApi.js'
import '../styles/Operations.css'

const DOC_ITEMS = [
  { key: 'aadhaar', label: 'Aadhar', comp_type: 'Aadhaar Verification' },
  { key: 'pan', label: 'PAN', comp_type: 'PAN Verification' },
  { key: 'uan', label: 'UAN', comp_type: 'UAN Linking' },
]

const DOC_STATUSES = ['pending', 'verified', 'rejected', 'missing']

function currentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function threeMonthsAgo() {
  const now = new Date()
  now.setMonth(now.getMonth() - 2)
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function formatInr(value) {
  if (value == null) return '-'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

function OperationsPage() {
  const navigate = useNavigate()
  const [employees, setEmployees] = useState([])
  const [selectedEmpId, setSelectedEmpId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [onboarding, setOnboarding] = useState(null)
  const [onboardingProgress, setOnboardingProgress] = useState(null)
  const [newDoc, setNewDoc] = useState({ key: 'aadhaar', status: 'pending', doc_url: '' })

  const [ctcHistory, setCtcHistory] = useState([])
  const [ctcForm, setCtcForm] = useState({
    int_title: '',
    ext_title: '',
    main_level: '',
    sub_level: 'A',
    start_of_ctc: '',
    end_of_ctc: '',
    ctc_amt: '',
  })
  const [exitDate, setExitDate] = useState(new Date().toISOString().slice(0, 10))

  const [complianceDashboard, setComplianceDashboard] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [compliancePagination, setCompliancePagination] = useState({
    limit: 10,
    offset: 0,
    returned: 0,
    total: 0,
    has_more: 0,
  })
  const [alertsPagination, setAlertsPagination] = useState({
    limit: 15,
    offset: 0,
    returned: 0,
    total: 0,
    has_more: 0,
  })
  const [joinersLeavers, setJoinersLeavers] = useState([])
  const [joinerRange, setJoinerRange] = useState({ start: threeMonthsAgo(), end: currentMonth() })
  const [ctcDistribution, setCtcDistribution] = useState({ salary_bands: [], level_counts: [] })
  const [complianceReport, setComplianceReport] = useState({ summary: null, items: [] })
  const [reportFilters, setReportFilters] = useState({ status: 'all', type: 'all' })

  const selectedEmployee = useMemo(
    () => employees.find((emp) => String(emp.emp_id) === String(selectedEmpId)) || null,
    [employees, selectedEmpId],
  )

  async function loadGlobal({
    complianceLimit = compliancePagination.limit,
    complianceOffset = compliancePagination.offset,
    alertsLimit = alertsPagination.limit,
    alertsOffset = alertsPagination.offset,
  } = {}) {
    const [progressRes, complianceRes, alertsRes, jlRes, ctcDistRes, reportRes] = await Promise.all([
      apiGetOnboardingProgress(),
      apiGetComplianceDashboard({ limit: complianceLimit, offset: complianceOffset }),
      apiGetAlerts({ limit: alertsLimit, offset: alertsOffset }),
      apiGetJoinersLeaversReport({ start_month: joinerRange.start, end_month: joinerRange.end }),
      apiGetCtcLevelDistribution(),
      apiGetComplianceStatusReport(reportFilters),
    ])
    setOnboardingProgress(progressRes?.data || null)
    setComplianceDashboard(complianceRes?.data || null)
    setAlerts(alertsRes?.data?.alerts || [])
    setCompliancePagination(
      complianceRes?.data?.pagination || {
        limit: complianceLimit,
        offset: complianceOffset,
        returned: 0,
        total: 0,
        has_more: 0,
      },
    )
    setAlertsPagination(
      alertsRes?.data?.pagination || {
        limit: alertsLimit,
        offset: alertsOffset,
        returned: 0,
        total: 0,
        has_more: 0,
      },
    )
    setJoinersLeavers(jlRes?.data?.months || [])
    setCtcDistribution(ctcDistRes?.data || { salary_bands: [], level_counts: [] })
    setComplianceReport({ summary: reportRes?.data?.summary || null, items: reportRes?.data?.items || [] })
  }

  async function loadEmployeeSections(empId) {
    if (!empId) {
      setOnboarding(null)
      setCtcHistory([])
      return
    }
    const [onboardRes, ctcRes] = await Promise.all([apiGetOnboarding(empId), apiGetCtcHistory(empId)])
    setOnboarding(onboardRes?.data || null)
    setCtcHistory(ctcRes?.data?.timeline || [])
  }

  async function initialLoad() {
    setLoading(true)
    setError('')
    try {
      const employeeRes = await apiListEmployees({ status: 'all', search: '', limit: 200, offset: 0 })
      const employeeItems = employeeRes?.data?.items || []
      setEmployees(employeeItems)
      if (!selectedEmpId && employeeItems.length > 0) {
        setSelectedEmpId(String(employeeItems[0].emp_id))
      }
      await loadGlobal()
    } catch (err) {
      setError(err?.message || 'Unable to load operations data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    initialLoad()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadEmployeeSections(selectedEmpId).catch((err) => setError(err?.message || 'Unable to load employee sections.'))
  }, [selectedEmpId])

  async function addDocument() {
    if (!selectedEmpId) return
    setError('')
    setMessage('')
    try {
      const selectedDoc = DOC_ITEMS.find((item) => item.key === newDoc.key)
      await apiAddDocument(selectedEmpId, {
        key: newDoc.key,
        comp_type: selectedDoc?.comp_type || newDoc.key,
        status: newDoc.status,
        doc_url: newDoc.doc_url,
      })
      setMessage('Document added. Checklist and compliance metrics updated.')
      setNewDoc((prev) => ({ ...prev, doc_url: '' }))
      await Promise.all([
        loadEmployeeSections(selectedEmpId),
        loadGlobal({ complianceOffset: 0, alertsOffset: 0 }),
      ])
    } catch (err) {
      setError(err?.message || 'Unable to add document.')
    }
  }

  async function updateDocumentStatus(docId, statusValue) {
    if (!selectedEmpId) return
    setError('')
    setMessage('')
    try {
      await apiUpdateDocument(selectedEmpId, docId, { status: statusValue })
      setMessage('Document status updated.')
      await Promise.all([
        loadEmployeeSections(selectedEmpId),
        loadGlobal({ complianceOffset: 0, alertsOffset: 0 }),
      ])
    } catch (err) {
      setError(err?.message || 'Unable to update document status.')
    }
  }

  async function addCtcRecord() {
    if (!selectedEmpId) return
    setError('')
    setMessage('')
    try {
      await apiAddCtcHistory(selectedEmpId, {
        ...ctcForm,
        main_level: Number(ctcForm.main_level),
        ctc_amt: Number(ctcForm.ctc_amt),
        end_of_ctc: ctcForm.end_of_ctc || null,
      })
      setMessage('CTC/Role change added to timeline.')
      setCtcForm({
        int_title: '',
        ext_title: '',
        main_level: '',
        sub_level: 'A',
        start_of_ctc: '',
        end_of_ctc: '',
        ctc_amt: '',
      })
      await Promise.all([
        loadEmployeeSections(selectedEmpId),
        loadGlobal({ complianceOffset: 0, alertsOffset: 0 }),
      ])
    } catch (err) {
      setError(err?.message || 'Unable to add CTC record.')
    }
  }

  async function runExitFlow() {
    if (!selectedEmpId) return
    setError('')
    setMessage('')
    try {
      await apiExitEmployee(selectedEmpId, exitDate)
      setMessage(`Employee marked inactive on ${exitDate}.`)
      await Promise.all([initialLoad(), loadEmployeeSections(selectedEmpId)])
    } catch (err) {
      setError(err?.message || 'Unable to process exit.')
    }
  }

  async function refreshReports() {
    setError('')
    try {
      await loadGlobal()
      setMessage('Reports refreshed.')
    } catch (err) {
      setError(err?.message || 'Unable to refresh reports.')
    }
  }

  async function changeCompliancePage(nextOffset) {
    setError('')
    try {
      await loadGlobal({ complianceOffset: nextOffset })
    } catch (err) {
      setError(err?.message || 'Unable to load compliance page.')
    }
  }

  async function changeAlertsPage(nextOffset) {
    setError('')
    try {
      await loadGlobal({ alertsOffset: nextOffset })
    } catch (err) {
      setError(err?.message || 'Unable to load alerts page.')
    }
  }

  return (
    <div className="ops-page">
      <section className="ops-hero">
        <div>
          <h1 className="display-2">HR Operations Hub</h1>
          <p className="lead-paragraph">
            Onboarding, document verification, role/CTC timeline, compliance alerts, and workforce reports.
          </p>
        </div>
        <div className="ops-hero-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => navigate('/home')}>
            Back to Home
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={refreshReports}>
            Refresh Metrics
          </button>
        </div>
      </section>

      <section className="ops-panel">
        <div className="ops-grid">
          <div>
            <label className="field-label" htmlFor="emp-select">Employee</label>
            <select
              id="emp-select"
              className="text-input"
              value={selectedEmpId}
              onChange={(e) => setSelectedEmpId(e.target.value)}
            >
              <option value="">Select Employee</option>
              {employees.map((emp) => (
                <option key={emp.emp_id} value={emp.emp_id}>
                  {emp.emp_id} - {emp.full_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label" htmlFor="exit-date">Last Working Day</label>
            <div className="inline-row">
              <input
                id="exit-date"
                type="date"
                className="text-input"
                value={exitDate}
                onChange={(e) => setExitDate(e.target.value)}
              />
              <button type="button" className="btn btn-ghost btn-sm" onClick={runExitFlow} disabled={!selectedEmpId}>
                Exit Employee
              </button>
            </div>
          </div>
        </div>
        {loading ? <p className="assistive-text">Loading operations hub...</p> : null}
        {message ? <p className="ops-success">{message}</p> : null}
        {error ? <p className="ops-error">{error}</p> : null}
      </section>

      <section className="ops-panel">
        <h2 className="heading-5">Onboarding Checklist & Document Collection</h2>
        <div className="ops-kpi-row">
          <article className="ops-kpi"><strong>{onboarding?.summary?.total_items || 0}</strong><span>Checklist Items</span></article>
          <article className="ops-kpi"><strong>{onboarding?.summary?.completed_items || 0}</strong><span>Completed</span></article>
          <article className="ops-kpi"><strong>{onboarding?.summary?.completion_percent || 0}%</strong><span>Progress</span></article>
          <article className="ops-kpi"><strong>{onboardingProgress?.metrics?.in_progress || 0}</strong><span>HR In Progress</span></article>
        </div>

        <div className="ops-two-col">
          <div>
            <h3 className="heading-6">Checklist</h3>
            <ul className="ops-list">
              {(onboarding?.checklist || []).map((item) => (
                <li key={item.key}>
                  <span>{item.label}</span>
                  <span className={`status-pill status-${item.status}`}>{item.status}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="heading-6">Add Document Entry</h3>
            <div className="ops-form-grid">
              <select
                className="text-input"
                value={newDoc.key}
                onChange={(e) => setNewDoc((prev) => ({ ...prev, key: e.target.value }))}
              >
                {DOC_ITEMS.map((item) => (
                  <option key={item.key} value={item.key}>{item.label}</option>
                ))}
              </select>
              <select
                className="text-input"
                value={newDoc.status}
                onChange={(e) => setNewDoc((prev) => ({ ...prev, status: e.target.value }))}
              >
                {DOC_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <input
                className="text-input"
                placeholder="Document link"
                value={newDoc.doc_url}
                onChange={(e) => setNewDoc((prev) => ({ ...prev, doc_url: e.target.value }))}
              />
              <button type="button" className="btn btn-primary btn-sm" onClick={addDocument} disabled={!selectedEmpId}>
                Add Document
              </button>
            </div>
          </div>
        </div>

        <h3 className="heading-6">Document Records</h3>
        <div className="table-wrap">
          <table className="ops-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Document Link</th>
                <th>Update</th>
              </tr>
            </thead>
            <tbody>
              {(onboarding?.documents || []).map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.id}</td>
                  <td>{doc.comp_type}</td>
                  <td>{doc.status}</td>
                  <td>{doc.doc_url ? <a href={doc.doc_url} target="_blank" rel="noreferrer">Open</a> : '-'}</td>
                  <td>
                    <select
                      className="text-input"
                      defaultValue={doc.status}
                      onChange={(e) => updateDocumentStatus(doc.id, e.target.value)}
                    >
                      {DOC_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {(onboarding?.documents || []).length === 0 ? (
                <tr><td colSpan="5">No document records yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="ops-panel">
        <h2 className="heading-5">Job/Role Change Tracking</h2>
        <div className="ops-form-grid ops-form-grid-wide">
          <input className="text-input" placeholder="Internal title" value={ctcForm.int_title} onChange={(e) => setCtcForm((p) => ({ ...p, int_title: e.target.value }))} />
          <input className="text-input" placeholder="External title" value={ctcForm.ext_title} onChange={(e) => setCtcForm((p) => ({ ...p, ext_title: e.target.value }))} />
          <input className="text-input" placeholder="Main level" value={ctcForm.main_level} onChange={(e) => setCtcForm((p) => ({ ...p, main_level: e.target.value }))} />
          <input className="text-input" placeholder="Sub level (A/B/C)" value={ctcForm.sub_level} onChange={(e) => setCtcForm((p) => ({ ...p, sub_level: e.target.value }))} />
          <input type="date" className="text-input" value={ctcForm.start_of_ctc} onChange={(e) => setCtcForm((p) => ({ ...p, start_of_ctc: e.target.value }))} />
          <input type="date" className="text-input" value={ctcForm.end_of_ctc} onChange={(e) => setCtcForm((p) => ({ ...p, end_of_ctc: e.target.value }))} />
          <input className="text-input" placeholder="CTC Amount" value={ctcForm.ctc_amt} onChange={(e) => setCtcForm((p) => ({ ...p, ctc_amt: e.target.value }))} />
          <button type="button" className="btn btn-primary btn-sm" onClick={addCtcRecord} disabled={!selectedEmpId}>
            Add CTC Record
          </button>
        </div>

        <div className="table-wrap">
          <table className="ops-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Level</th>
                <th>CTC</th>
                <th>From</th>
                <th>To</th>
              </tr>
            </thead>
            <tbody>
              {ctcHistory.map((row) => (
                <tr key={row.emp_ctc_id}>
                  <td>{row.ext_title} ({row.int_title})</td>
                  <td>{row.main_level}{row.sub_level}</td>
                  <td>{formatInr(row.ctc_amt)}</td>
                  <td>{row.start_of_ctc}</td>
                  <td>{row.end_of_ctc || 'Current'}</td>
                </tr>
              ))}
              {ctcHistory.length === 0 ? <tr><td colSpan="5">No CTC history available.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="ops-panel">
        <h2 className="heading-5">Compliance Dashboard & Alerts</h2>
        <div className="ops-kpi-row">
          <article className="ops-kpi"><strong>{complianceDashboard?.metrics?.total_compliance_records || 0}</strong><span>Total Compliance Records</span></article>
          <article className="ops-kpi"><strong>{complianceDashboard?.metrics?.missing_documents_count || 0}</strong><span>Missing Documents</span></article>
          <article className="ops-kpi"><strong>{complianceDashboard?.metrics?.pending_verification_count || 0}</strong><span>Pending Verification</span></article>
          <article className="ops-kpi"><strong>{complianceDashboard?.metrics?.employees_with_gaps || 0}</strong><span>Employees With Gaps</span></article>
        </div>

        <div className="ops-two-col">
          <div>
            <h3 className="heading-6">Employee Compliance Gaps</h3>
            <div className="table-wrap">
              <table className="ops-table">
                <thead><tr><th>Employee</th><th>Missing</th><th>Pending</th><th>Completion</th></tr></thead>
                <tbody>
                  {(complianceDashboard?.employees || []).map((row) => (
                    <tr key={row.emp_id}>
                      <td>{row.emp_id} - {row.employee_name}</td>
                      <td>{row.missing_documents.length}</td>
                      <td>{row.pending_documents.length}</td>
                      <td>{row.completion_percent}%</td>
                    </tr>
                  ))}
                  {!(complianceDashboard?.employees || []).length ? <tr><td colSpan="4">No records.</td></tr> : null}
                </tbody>
              </table>
            </div>
            <div className="ops-pagination">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={compliancePagination.offset <= 0}
                onClick={() => changeCompliancePage(Math.max(0, compliancePagination.offset - compliancePagination.limit))}
              >
                Previous
              </button>
              <span className="assistive-text">
                Showing {Math.min(compliancePagination.offset + 1, compliancePagination.total)}-
                {Math.min(compliancePagination.offset + compliancePagination.returned, compliancePagination.total)} of {compliancePagination.total}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!compliancePagination.has_more}
                onClick={() => changeCompliancePage(compliancePagination.offset + compliancePagination.limit)}
              >
                Next
              </button>
            </div>
          </div>

          <div>
            <h3 className="heading-6">Alerts / Reminders</h3>
            <ul className="ops-alerts">
              {alerts.map((alert) => (
                <li key={alert.alert_id}>
                  <span className={`status-pill status-${alert.severity === 'high' ? 'rejected' : 'pending'}`}>{alert.severity}</span>
                  <span>{alert.employee_name}: {alert.message}</span>
                </li>
              ))}
              {alerts.length === 0 ? <li>No active alerts.</li> : null}
            </ul>
            <div className="ops-pagination">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={alertsPagination.offset <= 0}
                onClick={() => changeAlertsPage(Math.max(0, alertsPagination.offset - alertsPagination.limit))}
              >
                Previous
              </button>
              <span className="assistive-text">
                Showing {Math.min(alertsPagination.offset + 1, alertsPagination.total)}-
                {Math.min(alertsPagination.offset + alertsPagination.returned, alertsPagination.total)} of {alertsPagination.total}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!alertsPagination.has_more}
                onClick={() => changeAlertsPage(alertsPagination.offset + alertsPagination.limit)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="ops-panel">
        <h2 className="heading-5">Reports & Analytics</h2>
        <div className="ops-two-col">
          <div>
            <h3 className="heading-6">Joiners & Leavers</h3>
            <div className="ops-form-grid">
              <input type="month" className="text-input" value={joinerRange.start} onChange={(e) => setJoinerRange((p) => ({ ...p, start: e.target.value }))} />
              <input type="month" className="text-input" value={joinerRange.end} onChange={(e) => setJoinerRange((p) => ({ ...p, end: e.target.value }))} />
              <button type="button" className="btn btn-secondary btn-sm" onClick={refreshReports}>Apply</button>
            </div>
            <div className="table-wrap">
              <table className="ops-table">
                <thead><tr><th>Month</th><th>Joiners</th><th>Leavers</th></tr></thead>
                <tbody>
                  {joinersLeavers.map((row) => (
                    <tr key={row.month}><td>{row.month}</td><td>{row.joiners}</td><td>{row.leavers}</td></tr>
                  ))}
                  {joinersLeavers.length === 0 ? <tr><td colSpan="3">No data in selected range.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="heading-6">CTC & Level Distribution</h3>
            <div className="table-wrap">
              <table className="ops-table">
                <thead><tr><th>Salary Band</th><th>Count</th></tr></thead>
                <tbody>
                  {(ctcDistribution.salary_bands || []).map((row) => (
                    <tr key={row.band}><td>{row.band}</td><td>{row.count}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-wrap">
              <table className="ops-table">
                <thead><tr><th>Level</th><th>Count</th></tr></thead>
                <tbody>
                  {(ctcDistribution.level_counts || []).map((row) => (
                    <tr key={row.level}><td>{row.level}</td><td>{row.count}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <h3 className="heading-6">Compliance Status Report</h3>
        <div className="ops-form-grid">
          <select className="text-input" value={reportFilters.status} onChange={(e) => setReportFilters((p) => ({ ...p, status: e.target.value }))}>
            <option value="all">All Statuses</option>
            {DOC_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="text-input" value={reportFilters.type} onChange={(e) => setReportFilters((p) => ({ ...p, type: e.target.value }))}>
            <option value="all">All Types</option>
            {DOC_ITEMS.map((d) => <option key={d.key} value={d.comp_type}>{d.label}</option>)}
          </select>
          <button type="button" className="btn btn-secondary btn-sm" onClick={refreshReports}>Filter</button>
        </div>
        <p className="assistive-text">
          Total: {complianceReport.summary?.total_records || 0},
          Pending: {complianceReport.summary?.pending || 0},
          Verified: {complianceReport.summary?.verified || 0},
          Non-compliant: {complianceReport.summary?.non_compliant || 0}
        </p>
        <div className="table-wrap">
          <table className="ops-table">
            <thead><tr><th>Employee</th><th>Type</th><th>Status</th><th>Doc</th></tr></thead>
            <tbody>
              {complianceReport.items.slice(0, 20).map((row) => (
                <tr key={row.document_id}>
                  <td>{row.emp_id} - {row.employee_name}</td>
                  <td>{row.comp_type}</td>
                  <td>{row.status}</td>
                  <td>{row.doc_url ? <a href={row.doc_url} target="_blank" rel="noreferrer">Open</a> : '-'}</td>
                </tr>
              ))}
              {complianceReport.items.length === 0 ? <tr><td colSpan="4">No compliance records.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      {selectedEmployee ? (
        <section className="ops-panel">
          <h2 className="heading-6">Selected Employee Snapshot</h2>
          <p className="assistive-text">
            {selectedEmployee.emp_id} - {selectedEmployee.full_name} | Status: {selectedEmployee.lifecycle_status}
          </p>
        </section>
      ) : null}
    </div>
  )
}

export default OperationsPage
