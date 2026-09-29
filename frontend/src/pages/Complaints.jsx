import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  TriangleAlert,
  Plus,
  Send,
  Eye,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  X,
  Loader2,
  Calendar,
  MessageSquare,
  ShieldCheck,
  Building2,
  Layers,
  HelpCircle,
  CheckCheck,
  RefreshCw
} from "lucide-react";
import { complaintService, projectService, authService } from "../services/api";
import "../styles/Modules.css";

export default function Complaints({ role: propRole }) {
  const navigate = useNavigate();

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          name: parsed.full_name || (parsed.first_name ? `${parsed.first_name} ${parsed.last_name || ""}`.trim() : parsed.email?.split("@")[0] || "User"),
          email: parsed.email || "",
          role: (parsed.role || "EMPLOYEE").toUpperCase(),
          photo: parsed.profile_photo_url || null,
        };
      }
    } catch {}
    return { name: "User", email: "", role: "EMPLOYEE", photo: null };
  });

  const isHr = (propRole || currentUser.role).toLowerCase() === "hr";

  const [complaints, setComplaints] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Filters (HR)
  const [filterType, setFilterType] = useState("ALL");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [filterPriority, setFilterPriority] = useState("ALL");
  const [filterSearch, setFilterSearch] = useState("");

  // Modals
  const [showRaiseModal, setShowRaiseModal] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);

  // Form State (Employee Raise Complaint)
  const [form, setForm] = useState({
    complaint_type: "COMPANY",
    project_id: "",
    subject: "",
    description: "",
    priority: "MEDIUM",
  });

  // HR Feedback Form State
  const [feedbackForm, setFeedbackForm] = useState({
    hr_response: "",
    status: "IN_REVIEW",
  });

  useEffect(() => {
    const fetchMe = () => {
      authService.getMe().then((me) => {
        if (me) {
          setCurrentUser({
            name: me.full_name || (me.first_name ? `${me.first_name} ${me.last_name || ""}`.trim() : me.email.split("@")[0]),
            email: me.email,
            role: (me.role || "EMPLOYEE").toUpperCase(),
            photo: me.profile_photo_url || null,
          });
        }
      }).catch(() => {});
    };
    fetchMe();

    const handleProfileUpdate = () => fetchMe();
    window.addEventListener("profileUpdated", handleProfileUpdate);
    window.addEventListener("storage", handleProfileUpdate);
    return () => {
      window.removeEventListener("profileUpdated", handleProfileUpdate);
      window.removeEventListener("storage", handleProfileUpdate);
    };
  }, []);

  // Load Projects for Employee Project Complaint dropdown
  const loadProjects = async () => {
    try {
      const myProjs = await projectService.getMyProjects();
      if (Array.isArray(myProjs)) {
        setProjects(myProjs);
        if (myProjs.length > 0 && !form.project_id) {
          setForm((prev) => ({ ...prev, project_id: myProjs[0].id }));
        }
      }
    } catch (err) {
      console.error("Load projects error:", err);
    }
  };

  // Load Complaints list
  const loadComplaints = async () => {
    setLoading(true);
    try {
      if (isHr) {
        const data = await complaintService.listHrComplaints();
        setComplaints(Array.isArray(data) ? data : (data?.items || []));
      } else {
        const data = await complaintService.listMyComplaints();
        setComplaints(Array.isArray(data) ? data : (data?.items || []));
      }
    } catch (err) {
      console.error("Failed to load complaints:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to load complaints." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
    loadComplaints();
  }, [isHr]);

  // Raise Complaint
  const handleRaiseSubmit = async (e) => {
    e.preventDefault();
    if (!form.subject.trim()) {
      setNotification({ type: "error", text: "Subject is required." });
      return;
    }
    if (!form.description.trim()) {
      setNotification({ type: "error", text: "Description is required." });
      return;
    }
    if (form.complaint_type === "PROJECT" && !form.project_id) {
      setNotification({ type: "error", text: "Please select an assigned project for project-related complaint." });
      return;
    }

    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      const payload = {
        complaint_type: form.complaint_type,
        project_id: form.complaint_type === "PROJECT" ? parseInt(form.project_id) : null,
        subject: form.subject.trim(),
        description: form.description.trim(),
        priority: form.priority,
      };

      await complaintService.create(payload);
      setNotification({
        type: "success",
        text: "Complaint submitted to HR successfully. You will be notified when HR reviews it.",
      });

      setShowRaiseModal(false);
      setForm({
        complaint_type: "COMPANY",
        project_id: projects[0]?.id || "",
        subject: "",
        description: "",
        priority: "MEDIUM",
      });
      await loadComplaints();
    } catch (err) {
      console.error("Raise complaint error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to submit complaint." });
    } finally {
      setSubmitting(false);
    }
  };

  // Open HR Review Modal
  const handleOpenReview = (c) => {
    setSelectedComplaint(c);
    setFeedbackForm({
      hr_response: c.hr_response || "",
      status: c.status === "OPEN" ? "IN_REVIEW" : c.status,
    });
    setShowReviewModal(true);
  };

  // Submit HR Feedback / Status Update
  const handleFeedbackSubmit = async (quickResolve = false) => {
    if (!selectedComplaint) return;
    const finalStatus = quickResolve ? "RESOLVED" : feedbackForm.status;

    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      await complaintService.provideFeedback(selectedComplaint.id, {
        hr_response: feedbackForm.hr_response.trim() || null,
        status: finalStatus,
      });

      setNotification({
        type: "success",
        text: `Complaint #${selectedComplaint.id} updated. The employee has been notified.`,
      });

      setShowReviewModal(false);
      setSelectedComplaint(null);
      await loadComplaints();
    } catch (err) {
      console.error("HR feedback error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to update complaint." });
    } finally {
      setSubmitting(false);
    }
  };

  // Filter complaints
  const filtered = complaints.filter((c) => {
    if (filterType !== "ALL" && c.complaint_type !== filterType) return false;
    if (filterStatus !== "ALL" && c.status !== filterStatus) return false;
    if (filterPriority !== "ALL" && c.priority !== filterPriority) return false;
    if (filterSearch) {
      const q = filterSearch.toLowerCase();
      const matchSub = c.subject?.toLowerCase().includes(q);
      const matchDesc = c.description?.toLowerCase().includes(q);
      const matchEmp = c.employee_name?.toLowerCase().includes(q);
      const matchCode = c.employee_code?.toLowerCase().includes(q);
      if (!matchSub && !matchDesc && !matchEmp && !matchCode) return false;
    }
    return true;
  });

  const getDashboardPath = () => (isHr ? "/hr/dashboard" : "/employee/dashboard");

  const getTypeIcon = (type) => {
    switch (type) {
      case "COMPANY":
        return <Building2 size={14} color="#2563eb" />;
      case "PROJECT":
        return <Layers size={14} color="#7c3aed" />;
      default:
        return <HelpCircle size={14} color="#0d9488" />;
    }
  };

  return (
    <div className="module-page-wrapper">
      {/* Header */}
      <header className="module-header-bar">
        <div className="module-header-container">
          <div className="module-header-left">
            <Link to={getDashboardPath()} className="module-back-btn">
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </Link>
            <div className="module-header-meta">
              <h2>{isHr ? "Complaints & Grievance Deck" : "My Workplace Complaints"}</h2>
              <span>{isHr ? "Review employee complaints and submit official resolution feedback" : "Submit confidential feedback and grievances to HR"}</span>
            </div>
          </div>

          <div className="module-header-right">
            {!isHr ? (
              <button
                className="module-action-btn primary"
                onClick={() => {
                  setForm({
                    complaint_type: "COMPANY",
                    project_id: projects[0]?.id || "",
                    subject: "",
                    description: "",
                    priority: "MEDIUM",
                  });
                  setShowRaiseModal(true);
                }}
              >
                <Plus size={16} />
                <span>Raise Complaint</span>
              </button>
            ) : (
              <button
                className="btn-secondary"
                onClick={loadComplaints}
                disabled={loading}
                title="Refresh complaints"
              >
                <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="module-main-container">
        {notification.text && (
          <div className={`module-alert-banner ${notification.type}`}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {notification.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
              <span>{notification.text}</span>
            </div>
            <button
              onClick={() => setNotification({ type: "", text: "" })}
              style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Filter Bar */}
        <div className="module-filter-bar">
          <input
            type="text"
            className="module-search-input"
            placeholder={isHr ? "Search by subject, employee, or details..." : "Search complaints..."}
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
          />

          <select
            className="module-select"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="ALL">All Types</option>
            <option value="COMPANY">Company-related</option>
            <option value="PROJECT">Project-related</option>
            <option value="OTHER">Other work-related</option>
          </select>

          <select
            className="module-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_REVIEW">In Review</option>
            <option value="RESPONDED">Responded</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            className="module-select"
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
          >
            <option value="ALL">All Priorities</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
        </div>

        {/* Complaints Table */}
        <div className="module-table-container">
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
              <Loader2 size={24} className="spin-animation" />
              <span>Loading complaints...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="module-empty-box">
              <TriangleAlert size={40} className="module-empty-icon" />
              <div className="module-empty-title">No complaints found</div>
              <div className="module-empty-desc">
                {filterSearch || filterType !== "ALL" || filterStatus !== "ALL" || filterPriority !== "ALL"
                  ? "No records matched your search filters."
                  : isHr
                  ? "No employee complaints have been submitted."
                  : "You have not raised any workplace complaints."}
              </div>
              {!isHr && (
                <button
                  className="module-action-btn primary"
                  onClick={() => setShowRaiseModal(true)}
                >
                  <Plus size={15} /> Raise a Complaint
                </button>
              )}
            </div>
          ) : (
            <table className="module-table">
              <thead>
                <tr>
                  <th style={{ width: "80px" }}>ID</th>
                  {isHr && <th>Employee</th>}
                  <th style={{ width: "130px" }}>Type</th>
                  <th>Subject</th>
                  <th style={{ width: "110px" }}>Priority</th>
                  <th style={{ width: "130px" }}>Status</th>
                  <th style={{ width: "140px" }}>Created Date</th>
                  <th style={{ width: "120px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600, color: "#64748b", fontSize: "13px" }}>
                      #{c.id}
                    </td>
                    {isHr && (
                      <td>
                        <div style={{ fontWeight: 600, color: "#0f172a", fontSize: "14px" }}>
                          {c.employee_name || "Employee"}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748b" }}>
                          {c.employee_code || `ID: ${c.employee_id}`}
                        </div>
                      </td>
                    )}
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "13px", fontWeight: 600, color: "#334155" }}>
                        {getTypeIcon(c.complaint_type)}
                        {c.complaint_type}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: "#0f172a", fontSize: "14px" }}>
                        {c.subject}
                      </div>
                      {c.project_name && (
                        <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
                          Project: {c.project_name}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`module-priority-badge ${c.priority}`}>
                        {c.priority}
                      </span>
                    </td>
                    <td>
                      <span className={`module-status-badge ${c.status}`}>
                        {c.status}
                      </span>
                    </td>
                    <td style={{ fontSize: "13px", color: "#475569" }}>
                      {c.created_at ? new Date(c.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {isHr ? (
                        <button
                          className="module-action-btn primary"
                          style={{ padding: "5px 12px", fontSize: "12px" }}
                          onClick={() => handleOpenReview(c)}
                        >
                          <ShieldCheck size={13} /> Review
                        </button>
                      ) : (
                        <button
                          className="module-action-btn secondary"
                          style={{ padding: "5px 12px", fontSize: "12px" }}
                          onClick={() => setSelectedComplaint(c)}
                        >
                          <Eye size={13} /> View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {/* EMPLOYEE RAISE COMPLAINT MODAL */}
      {showRaiseModal && !isHr && (
        <div className="module-modal-overlay" onClick={() => setShowRaiseModal(false)}>
          <div className="module-modal-dialog modal-complaint" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <TriangleAlert size={20} color="#dc2626" />
                  <span>Raise a Complaint</span>
                </h3>
                <p className="module-modal-subtitle">
                  Submit a company or project-related complaint for HR review.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowRaiseModal(false)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleRaiseSubmit}>
              <div className="module-modal-body">
                <div className="form-grid">
                  <div className="form-section-header">
                    Complaint Information
                  </div>

                  <div className="form-field">
                    <label>
                      Complaint Type <span className="required-star">*</span>
                    </label>
                    <select
                      value={form.complaint_type}
                      onChange={(e) => setForm({ ...form, complaint_type: e.target.value })}
                      required
                    >
                      <option value="COMPANY">Company-related Complaint</option>
                      <option value="PROJECT">Project-related Complaint</option>
                      <option value="OTHER">Other Work-related Complaint</option>
                    </select>
                  </div>

                  <div className="form-field">
                    <label>
                      Priority <span className="required-star">*</span>
                    </label>
                    <select
                      value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: e.target.value })}
                      required
                    >
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="URGENT">Urgent</option>
                    </select>
                  </div>

                  {/* Show Project ONLY if type is PROJECT */}
                  {form.complaint_type === "PROJECT" && (
                    <div className="form-field form-field-full">
                      <label>
                        Project <span className="required-star">*</span>
                      </label>
                      <select
                        value={form.project_id}
                        onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                        required
                      >
                        {projects.length === 0 ? (
                          <option value="">No assigned projects found</option>
                        ) : (
                          projects.map((p) => (
                            <option key={p.id} value={p.id}>{p.title || p.name}</option>
                          ))
                        )}
                      </select>
                      <span className="form-field-helper">
                        Only projects currently assigned to you are available.
                      </span>
                    </div>
                  )}

                  <div className="form-field form-field-full">
                    <label>
                      Subject <span className="required-star">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Brief summary of the issue..."
                      value={form.subject}
                      onChange={(e) => setForm({ ...form, subject: e.target.value })}
                      maxLength={255}
                      required
                    />
                  </div>

                  <div className="form-section-header">
                    Complaint Details
                  </div>

                  <div className="form-field form-field-full">
                    <label>
                      Description <span className="required-star">*</span>
                    </label>
                    <textarea
                      className="textarea-tall"
                      placeholder="Please provide full details, dates, and background for HR investigation..."
                      value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="module-modal-footer">
                <button
                  type="button"
                  className="module-action-btn secondary"
                  onClick={() => setShowRaiseModal(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="module-action-btn primary"
                  disabled={submitting}
                >
                  {submitting ? <Loader2 size={14} className="spin-animation" /> : <><Send size={14} /> Submit Complaint</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EMPLOYEE VIEW COMPLAINT DETAILS MODAL */}
      {selectedComplaint && !isHr && (
        <div className="module-modal-overlay" onClick={() => setSelectedComplaint(null)}>
          <div className="module-modal-dialog modal-complaint" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <TriangleAlert size={20} color="#dc2626" />
                  <span>Complaint #{selectedComplaint.id}: {selectedComplaint.subject}</span>
                </h3>
                <p className="module-modal-subtitle">
                  Workplace complaint tracking and status details
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedComplaint(null)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              <div className="info-grid">
                <div className="info-cell">
                  <span className="info-cell-label">Category</span>
                  <div className="info-cell-value" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {getTypeIcon(selectedComplaint.complaint_type)}
                    <span>{selectedComplaint.complaint_type}</span>
                  </div>
                </div>

                {selectedComplaint.project_name && (
                  <div className="info-cell">
                    <span className="info-cell-label">Project</span>
                    <div className="info-cell-value">{selectedComplaint.project_name}</div>
                  </div>
                )}

                <div className="info-cell">
                  <span className="info-cell-label">Priority</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedComplaint.priority.toLowerCase()}`}>
                      {selectedComplaint.priority}
                    </span>
                  </div>
                </div>

                <div className="info-cell">
                  <span className="info-cell-label">Status</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedComplaint.status.toLowerCase()}`}>
                      {selectedComplaint.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="form-section-header">
                Original Complaint Description
              </div>
              <div className="detail-content-box">
                {selectedComplaint.description}
              </div>

              <div className="form-section-header">
                HR Response / Feedback
              </div>
              {selectedComplaint.hr_response ? (
                <div className="detail-response-box">
                  {selectedComplaint.hr_response}
                </div>
              ) : (
                <div style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", padding: "16px", borderRadius: "10px", fontSize: "13px", color: "#64748b", fontStyle: "italic" }}>
                  HR has not provided written feedback yet. Your complaint is currently being investigated.
                </div>
              )}
            </div>

            <div className="module-modal-footer">
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setSelectedComplaint(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HR REVIEW & FEEDBACK MODAL */}
      {showReviewModal && selectedComplaint && isHr && (
        <div className="module-modal-overlay" onClick={() => setShowReviewModal(false)}>
          <div className="module-modal-dialog modal-complaint" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <ShieldCheck size={20} color="#047857" />
                  <span>Review Complaint #{selectedComplaint.id}</span>
                </h3>
                <p className="module-modal-subtitle">
                  Complaint information and formal HR resolution
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowReviewModal(false)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              {/* Complaint Overview Grid */}
              <div className="form-section-header" style={{ marginTop: 0 }}>
                Employee & Complaint Overview
              </div>
              <div className="info-grid">
                <div className="info-cell">
                  <span className="info-cell-label">Employee</span>
                  <div className="info-cell-value">{selectedComplaint.employee_name || "Employee"} ({selectedComplaint.employee_code})</div>
                </div>

                <div className="info-cell">
                  <span className="info-cell-label">Category / Project</span>
                  <div className="info-cell-value">
                    {selectedComplaint.complaint_type} {selectedComplaint.project_name ? `• ${selectedComplaint.project_name}` : ""}
                  </div>
                </div>

                <div className="info-cell">
                  <span className="info-cell-label">Priority</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedComplaint.priority.toLowerCase()}`}>
                      {selectedComplaint.priority}
                    </span>
                  </div>
                </div>

                <div className="info-cell">
                  <span className="info-cell-label">Current Status</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedComplaint.status.toLowerCase()}`}>
                      {selectedComplaint.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Subject & Description */}
              <div className="form-section-header">
                Complaint Details
              </div>

              <div className="form-field">
                <span className="info-cell-label" style={{ marginBottom: "4px" }}>Subject</span>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "15px", marginBottom: "8px" }}>
                  {selectedComplaint.subject}
                </div>
              </div>

              <div className="form-field">
                <span className="info-cell-label" style={{ marginBottom: "6px" }}>Employee Description</span>
                <div className="detail-content-box" style={{ maxHeight: "150px", overflowY: "auto" }}>
                  {selectedComplaint.description}
                </div>
              </div>

              {/* HR Response Controls */}
              <div className="form-section-header">
                HR Response / Feedback
              </div>

              <div className="form-grid">
                <div className="form-field form-field-full">
                  <label>
                    HR Response / Feedback to Employee
                  </label>
                  <textarea
                    className="textarea-tall"
                    placeholder="Enter formal response, resolution details, or action plan..."
                    value={feedbackForm.hr_response}
                    onChange={(e) => setFeedbackForm({ ...feedbackForm, hr_response: e.target.value })}
                  />
                  <div className="form-field-helper">
                    The employee will receive an in-app notification when you respond.
                  </div>
                </div>

                <div className="form-section-header">
                  Update Complaint Status
                </div>

                <div className="form-field form-field-full">
                  <label>Update Status</label>
                  <select
                    value={feedbackForm.status}
                    onChange={(e) => setFeedbackForm({ ...feedbackForm, status: e.target.value })}
                  >
                    <option value="IN_REVIEW">In Review</option>
                    <option value="RESPONDED">Responded</option>
                    <option value="RESOLVED">Resolved</option>
                    <option value="CLOSED">Closed</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="module-modal-footer">
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setShowReviewModal(false)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="module-action-btn secondary"
                style={{ color: "#16a34a", borderColor: "#86efac" }}
                onClick={() => handleFeedbackSubmit(true)}
                disabled={submitting}
              >
                <CheckCheck size={14} /> Quick Resolve
              </button>
              <button
                type="button"
                className="module-action-btn primary"
                onClick={() => handleFeedbackSubmit(false)}
                disabled={submitting}
              >
                {submitting ? <Loader2 size={14} className="spin-animation" /> : <><Send size={14} /> Save Feedback & Update</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
