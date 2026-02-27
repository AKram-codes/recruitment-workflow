import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiGetEmployeeProfile } from '../api/employeeApi.js'
import '../styles/Profile.css'

function formatDate(value) {
  if (!value) return 'Not available'
  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: '2-digit' })
}

function formatCurrency(amount) {
  if (typeof amount !== 'number') return 'Not available'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

function valueOrMissing(value) {
  return value || 'Not available'
}

function ProfilePage() {
  const { empId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function loadProfile() {
      setLoading(true)
      setError('')
      try {
        const payload = await apiGetEmployeeProfile(empId)
        if (cancelled) return
        setProfile(payload?.data || null)
      } catch (err) {
        if (cancelled) return
        setProfile(null)
        setError(err?.message || 'Unable to load employee profile.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadProfile()
    return () => {
      cancelled = true
    }
  }, [empId])

  const personal = profile?.personal || null
  const bank = profile?.bank || null
  const registration = profile?.compliance?.registration_ids || {}
  const complianceTracker = profile?.compliance?.tracker || []
  const ctcTimeline = profile?.ctc_timeline || []
  const missingSections = profile?.missing_sections || []
  const allComplianceIdsMissing =
    !registration.pan && !registration.aadhaar && !registration.uan_epf_acctno && !registration.esi

  return (
    <div className="profile-page">
      <section className="hero-section reveal">
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          <span>Employee CRUD Management</span>
          <span>/</span>
          <span aria-current="page">Unified Employee Profile</span>
        </nav>

        <div className="profile-header">
          <div>
            <h1 className="display-2">
              {personal?.full_name || `Employee ${empId}`}
            </h1>
            <p className="lead-paragraph">
              Unified profile across personal details, bank, compliance IDs, and CTC timeline.
            </p>
          </div>

          <div className="profile-header-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => navigate('/home')}>
              Back to List
            </button>
          </div>
        </div>
      </section>

      <main className="profile-grid reveal delay-1">
        {loading ? (
          <section className="panel profile-panel">
            <p className="assistive-text">Loading employee profile...</p>
          </section>
        ) : null}

        {!loading && error ? (
          <section className="panel profile-panel">
            <p className="feedback error">{error}</p>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => navigate('/home')}>
              Return to Employee List
            </button>
          </section>
        ) : null}

        {!loading && !error && personal ? (
          <>
            <section className="panel profile-panel">
              <div className="panel-head">
                <h2 className="heading-5">Personal Details</h2>
              </div>
              <div className="profile-detail-grid">
                <div>
                  <span className="profile-label">Employee ID</span>
                  <p>{personal.emp_id}</p>
                </div>
                <div>
                  <span className="profile-label">Lifecycle Status</span>
                  <p>{valueOrMissing(personal.lifecycle_status)}</p>
                </div>
                <div>
                  <span className="profile-label">First Name</span>
                  <p>{valueOrMissing(personal.first_name)}</p>
                </div>
                <div>
                  <span className="profile-label">Middle Name</span>
                  <p>{valueOrMissing(personal.middle_name)}</p>
                </div>
                <div>
                  <span className="profile-label">Last Name</span>
                  <p>{valueOrMissing(personal.last_name)}</p>
                </div>
                <div>
                  <span className="profile-label">Start Date</span>
                  <p>{formatDate(personal.start_date)}</p>
                </div>
                <div>
                  <span className="profile-label">End Date</span>
                  <p>{formatDate(personal.end_date)}</p>
                </div>
              </div>
            </section>

            <section className="panel profile-panel">
              <div className="panel-head">
                <h2 className="heading-5">Bank Details</h2>
              </div>
              {bank ? (
                <div className="profile-detail-grid">
                  <div>
                    <span className="profile-label">Bank Name</span>
                    <p>{valueOrMissing(bank.bank_name)}</p>
                  </div>
                  <div>
                    <span className="profile-label">Branch</span>
                    <p>{valueOrMissing(bank.branch_name)}</p>
                  </div>
                  <div>
                    <span className="profile-label">Account Number</span>
                    <p>{valueOrMissing(bank.bank_acct_no)}</p>
                  </div>
                  <div>
                    <span className="profile-label">IFSC</span>
                    <p>{valueOrMissing(bank.ifsc_code)}</p>
                  </div>
                </div>
              ) : (
                <p className="assistive-text">Bank details are not available for this employee.</p>
              )}
            </section>

            <section className="panel profile-panel">
              <div className="panel-head">
                <h2 className="heading-5">Compliance</h2>
              </div>

              <h3 className="heading-6 section-subtitle">Compliance IDs</h3>
              <div className="profile-detail-grid">
                <div>
                  <span className="profile-label">PAN</span>
                  <p>{valueOrMissing(registration.pan)}</p>
                </div>
                <div>
                  <span className="profile-label">Aadhaar</span>
                  <p>{valueOrMissing(registration.aadhaar)}</p>
                </div>
                <div>
                  <span className="profile-label">UAN/EPF</span>
                  <p>{valueOrMissing(registration.uan_epf_acctno)}</p>
                </div>
                <div>
                  <span className="profile-label">ESI</span>
                  <p>{valueOrMissing(registration.esi)}</p>
                </div>
              </div>
              {allComplianceIdsMissing ? (
                <p className="assistive-text">Compliance registration IDs are not available.</p>
              ) : null}

              <h3 className="heading-6 section-subtitle">Compliance Tracker</h3>
              {complianceTracker.length === 0 ? (
                <p className="assistive-text">Compliance tracker entries are not available.</p>
              ) : (
                <div className="tracker-list">
                  {complianceTracker.map((item, index) => (
                    <article key={`comp-${index}`} className="tracker-item">
                      <div className="tracker-main">
                        <strong>{item.comp_type || 'Compliance Item'}</strong>
                        <span className={`tracker-status tracker-${String(item.status || '').toLowerCase()}`}>
                          {valueOrMissing(item.status)}
                        </span>
                      </div>
                      <p className="assistive-text">
                        {item.doc_url ? (
                          <a href={item.doc_url} target="_blank" rel="noreferrer">
                            {item.doc_url}
                          </a>
                        ) : (
                          'Document URL not available'
                        )}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="panel profile-panel">
              <div className="panel-head">
                <h2 className="heading-5">CTC Timeline</h2>
              </div>
              {ctcTimeline.length === 0 ? (
                <p className="assistive-text">No CTC history available for this employee.</p>
              ) : (
                <ol className="ctc-timeline">
                  {ctcTimeline.map((item, index) => (
                    <li key={`ctc-${index}`} className="ctc-item">
                      <div className="ctc-head">
                        <strong>{valueOrMissing(item.ext_title)}</strong>
                        <span>{formatCurrency(item.ctc_amt)}</span>
                      </div>
                      <p className="assistive-text">
                        {valueOrMissing(item.int_title)} | Level {valueOrMissing(item.main_level)}
                        {item.sub_level ? item.sub_level : ''}
                      </p>
                      <p className="assistive-text">
                        {formatDate(item.start_of_ctc)} to {formatDate(item.end_of_ctc)}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            {missingSections.length > 0 ? (
              <section className="panel profile-panel">
                <div className="panel-head">
                  <h2 className="heading-6">Missing Data Summary</h2>
                </div>
                <p className="assistive-text">
                  Some profile sections are unavailable: {missingSections.join(', ')}.
                </p>
              </section>
            ) : null}
          </>
        ) : null}
      </main>
    </div>
  )
}

export default ProfilePage
