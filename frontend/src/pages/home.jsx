import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  apiCreateEmployee,
  apiExitEmployee,
  apiListEmployees,
  apiUpdateEmployee,
} from '../api/employeeApi.js'
import '../styles/Home.css'

const EMPTY_FORM = {
  emp_id: '',
  first_name: '',
  middle_name: '',
  last_name: '',
  start_date: '',
}

function getInitials(employee) {
  const first = (employee?.first_name || '').trim().charAt(0)
  const last = (employee?.last_name || '').trim().charAt(0)
  return `${first}${last}`.toUpperCase() || '--'
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function HomePage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('name_asc')
  const [search, setSearch] = useState('')
  const [employees, setEmployees] = useState([])
  const [counts, setCounts] = useState({ total: 0, active: 0, exited: 0 })
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [formErrors, setFormErrors] = useState({})
  const [formMode, setFormMode] = useState('create')
  const [editingEmpId, setEditingEmpId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [exitDates, setExitDates] = useState({})

  const [avatarFile, setAvatarFile] = useState('')
  const [docsConfirmed, setDocsConfirmed] = useState(true)
  const [employmentType, setEmploymentType] = useState('full_time')
  const [notifyOps, setNotifyOps] = useState(false)

  const headlineCount = useMemo(() => `${counts.active} Active / ${counts.exited} Exited`, [counts])
  const sortedEmployees = useMemo(() => {
    const items = [...employees]

    if (sortBy === 'name_asc' || sortBy === 'name_desc') {
      items.sort((a, b) => {
        const nameA = (a.full_name || '').trim().toLowerCase()
        const nameB = (b.full_name || '').trim().toLowerCase()
        const cmp = nameA.localeCompare(nameB)
        if (cmp !== 0) return sortBy === 'name_asc' ? cmp : -cmp
        return (a.emp_id || 0) - (b.emp_id || 0)
      })
      return items
    }

    if (sortBy === 'start_date') {
      items.sort((a, b) => {
        const dateA = Date.parse(a.start_date || '') || 0
        const dateB = Date.parse(b.start_date || '') || 0
        if (dateA !== dateB) return dateA - dateB
        return (a.emp_id || 0) - (b.emp_id || 0)
      })
    }

    return items
  }, [employees, sortBy])

  useEffect(() => {
    let cancelled = false

    async function loadEmployees() {
      setLoading(true)
      setError('')
      try {
        const data = await apiListEmployees({
          status: statusFilter,
          search: search.trim(),
          limit: 60,
          offset: 0,
        })

        if (cancelled) return

        const items = data?.data?.items || []
        setEmployees(items)
        setCounts(data?.data?.counts || { total: 0, active: 0, exited: 0 })
      } catch (err) {
        if (cancelled) return
        setError(err?.message || 'Unable to fetch employees.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadEmployees()
    return () => {
      cancelled = true
    }
  }, [statusFilter, search])

  function setField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setFormErrors((prev) => ({ ...prev, [field]: '' }))
  }

  function resetForm() {
    setForm(EMPTY_FORM)
    setFormErrors({})
    setFormMode('create')
    setEditingEmpId(null)
    setAvatarFile('')
    setDocsConfirmed(true)
    setEmploymentType('full_time')
    setNotifyOps(false)
  }

  function validate() {
    const nextErrors = {}
    const empId = Number(form.emp_id)

    if (!Number.isInteger(empId) || empId <= 0) {
      nextErrors.emp_id = 'Emp ID must be a positive integer.'
    }
    if (!form.first_name.trim()) {
      nextErrors.first_name = 'First name is mandatory.'
    }
    if (!form.last_name.trim()) {
      nextErrors.last_name = 'Last name is mandatory.'
    }
    if (!form.start_date) {
      nextErrors.start_date = 'Start date is mandatory.'
    }
    if (!docsConfirmed) {
      nextErrors.docsConfirmed = 'Confirm documentation before submit.'
    }

    setFormErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  async function reload() {
    setLoading(true)
    try {
      const data = await apiListEmployees({
        status: statusFilter,
        search: search.trim(),
        limit: 60,
        offset: 0,
      })
      setEmployees(data?.data?.items || [])
      setCounts(data?.data?.counts || { total: 0, active: 0, exited: 0 })
    } catch (err) {
      setError(err?.message || 'Unable to fetch employees.')
    } finally {
      setLoading(false)
    }
  }

  async function onSubmitEmployee(event) {
    event.preventDefault()
    if (submitting) return
    if (!validate()) return

    setSubmitting(true)
    setError('')
    setMessage('')

    const payload = {
      emp_id: Number(form.emp_id),
      first_name: form.first_name.trim(),
      middle_name: form.middle_name.trim() || null,
      last_name: form.last_name.trim(),
      start_date: form.start_date,
    }

    try {
      if (formMode === 'create') {
        await apiCreateEmployee(payload)
        setMessage('Employee created successfully.')
      } else if (editingEmpId !== null) {
        await apiUpdateEmployee(editingEmpId, {
          first_name: payload.first_name,
          middle_name: payload.middle_name,
          last_name: payload.last_name,
          start_date: payload.start_date,
        })
        setMessage('Employee updated successfully.')
      }

      resetForm()
      await reload()
    } catch (err) {
      setError(err?.message || 'Unable to save employee.')
      setFormErrors((prev) => ({ ...prev, ...(err?.payload?.errors || {}) }))
    } finally {
      setSubmitting(false)
    }
  }

  function onEdit(employee) {
    setFormMode('edit')
    setEditingEmpId(employee.emp_id)
    setForm({
      emp_id: String(employee.emp_id),
      first_name: employee.first_name || '',
      middle_name: employee.middle_name || '',
      last_name: employee.last_name || '',
      start_date: employee.start_date || '',
    })
    setError('')
    setMessage(`Editing employee ${employee.emp_id}.`)
  }

  async function onExit(employee) {
    const chosenDate = exitDates[employee.emp_id] || todayIso()
    setSubmitting(true)
    setError('')
    setMessage('')
    try {
      await apiExitEmployee(employee.emp_id, chosenDate)
      setMessage(`Employee ${employee.emp_id} marked as exited on ${chosenDate}.`)
      setExitDates((prev) => {
        const next = { ...prev }
        delete next[employee.emp_id]
        return next
      })
      await reload()
    } catch (err) {
      setError(err?.message || 'Unable to deactivate employee.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="employee-page">
      <section className="hero-section reveal">
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          
          <span aria-current="page">Employee CRUD Management</span>
        </nav>

        <div className="hero-header">
          <div>
            <h1 className="display-2">Employee CRUD Management</h1>
            <p className="lead-paragraph">
              Create, update, and deactivate employees with consistent data in the employee master
              table and complete active/exited visibility.
            </p>
            <div style={{ marginTop: '16px' }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => navigate('/operations')}
              >
                Open HR Operations Hub
              </button>
            </div>
          </div>
          <div className="hero-metric">
            <div className="metric-value">{counts.total}</div>
            <div className="metric-label">Total Employees</div>
            <div className="metric-sub">{headlineCount}</div>
          </div>
        </div>
      </section>
      
      <main className="content-grid reveal delay-2">
        <section className="panel form-panel">
          <div className="panel-head">
            <h2 className="heading-5">{formMode === 'create' ? 'Add Employee' : 'Edit Employee'}</h2>
            {formMode === 'edit' ? (
              <button type="button" className="btn btn-ghost btn-sm" onClick={resetForm}>
                Cancel Edit
              </button>
            ) : null}
          </div>

          <form className="employee-form" onSubmit={onSubmitEmployee}>
            <div className="form-field">
              <label className="field-label" htmlFor="emp_id">
                Employee ID
              </label>
              <input
                id="emp_id"
                className={`text-input ${formErrors.emp_id ? 'has-error' : ''}`}
                value={form.emp_id}
                onChange={(e) => setField('emp_id', e.target.value)}
                disabled={formMode === 'edit'}
                placeholder="Example: 240101"
              />
              <p className="assistive-text">Mandatory and unique across employee master.</p>
              {formErrors.emp_id ? <p className="error-text">{formErrors.emp_id}</p> : null}
            </div>

            <div className="name-grid">
              <div className="form-field">
                <label className="field-label" htmlFor="first_name">
                  First Name
                </label>
                <input
                  id="first_name"
                  className={`text-input ${formErrors.first_name ? 'has-error' : ''}`}
                  value={form.first_name}
                  onChange={(e) => setField('first_name', e.target.value)}
                />
                {formErrors.first_name ? <p className="error-text">{formErrors.first_name}</p> : null}
              </div>

              <div className="form-field">
                <label className="field-label" htmlFor="middle_name">
                  Middle Name
                </label>
                <input
                  id="middle_name"
                  className={`text-input ${formErrors.middle_name ? 'has-error' : ''}`}
                  value={form.middle_name}
                  onChange={(e) => setField('middle_name', e.target.value)}
                />
                {formErrors.middle_name ? <p className="error-text">{formErrors.middle_name}</p> : null}
              </div>

              <div className="form-field">
                <label className="field-label" htmlFor="last_name">
                  Last Name
                </label>
                <input
                  id="last_name"
                  className={`text-input ${formErrors.last_name ? 'has-error' : ''}`}
                  value={form.last_name}
                  onChange={(e) => setField('last_name', e.target.value)}
                />
                {formErrors.last_name ? <p className="error-text">{formErrors.last_name}</p> : null}
              </div>
            </div>

            <div className="form-field">
              <label className="field-label" htmlFor="start_date">
                Start Date
              </label>
              <input
                id="start_date"
                type="date"
                className={`text-input ${formErrors.start_date ? 'has-error' : ''}`}
                value={form.start_date}
                onChange={(e) => setField('start_date', e.target.value)}
              />
              {formErrors.start_date ? <p className="error-text">{formErrors.start_date}</p> : null}
            </div>

            <label className="check-wrap">
              <input
                type="checkbox"
                checked={docsConfirmed}
                onChange={(e) => setDocsConfirmed(e.target.checked)}
              />
              <span>I confirm mandatory compliance documents are available.</span>
            </label>
            {formErrors.docsConfirmed ? <p className="error-text">{formErrors.docsConfirmed}</p> : null}

            <div className="form-actions">
              <button type="submit" className="btn btn-primary btn-md" disabled={submitting}>
                {submitting ? 'Saving...' : formMode === 'create' ? 'Create Employee' : 'Update Employee'}
              </button>
              <button type="button" className="btn btn-secondary btn-md" onClick={reload} disabled={loading}>
                Refresh List
              </button>
            </div>
          </form>
        </section>

        <section className="panel list-panel">
          <div className="panel-head">
            <h2 className="heading-5">Employee Registry</h2>
            <div className="badge">{counts.total} records</div>
          </div>

          <div className="filter-bar">
            <select
              className="text-input"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Employees</option>
              <option value="active">Active</option>
              <option value="exited">Exited</option>
            </select>
            <input
              className="text-input"
              placeholder="Search by name or emp id"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select className="text-input" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
              <option value="start_date">Start Date</option>
            </select>
          </div>

          {message ? <p className="feedback success">{message}</p> : null}
          {error ? <p className="feedback error">{error}</p> : null}

          <div className="employee-list">
            {loading ? <p className="assistive-text">Loading employees...</p> : null}
            {!loading && employees.length === 0 ? (
              <p className="assistive-text">No employees found for the selected filter.</p>
            ) : null}

            {sortedEmployees.map((employee) => (
              <article className="employee-row" key={employee.emp_id}>
                <div className="employee-main">
                  <span className="avatar avatar-md">{getInitials(employee)}</span>
                  <div>
                    <div className="employee-name">{employee.full_name}</div>
                    <div className="employee-meta">
                      <span>ID: {employee.emp_id}</span>
                      <span>Start: {employee.start_date}</span>
                      <span>Status: {employee.lifecycle_status}</span>
                      {employee.end_date ? <span>End: {employee.end_date}</span> : null}
                    </div>
                  </div>
                </div>

                <div className="employee-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate(`/employees/${employee.emp_id}/profile`)}
                  >
                    View Profile
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => onEdit(employee)}
                    disabled={submitting}
                  >
                    Edit
                  </button>

                  {employee.lifecycle_status === 'active' ? (
                    <>
                      <input
                        type="date"
                        className="text-input exit-date"
                        value={exitDates[employee.emp_id] || todayIso()}
                        onChange={(e) =>
                          setExitDates((prev) => ({ ...prev, [employee.emp_id]: e.target.value }))
                        }
                      />
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => onExit(employee)}
                        disabled={submitting}
                      >
                        Deactivate
                      </button>
                    </>
                  ) : (
                    <button type="button" className="btn btn-ghost btn-sm" disabled>
                      Exited
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default HomePage
