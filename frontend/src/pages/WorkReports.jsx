import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FileChartColumn,
  Plus,
  Send,
  Eye,
  Edit2,
  Trash2,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  X,
  Loader2,
  Calendar,
  Clock,
  Briefcase,
  User,
  Filter,
  Search,
  FileText,
  Users,
} from "lucide-react";
import { workReportService, projectService, authService } from "../services/api";
import "../styles/Modules.css";

export default function WorkReports({ role: propRole }) {
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

  const [activeTab, setActiveTab] = useState(isHr ? "employee-reports" : "my-reports");
  const [myReports, setMyReports] = useState([]);
  const [employeeReports, setEmployeeReports] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [projectLoadError, setProjectLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Filters for HR Employee Reports
  const [filterEmployee, setFilterEmployee] = useState("");
  const [filterProject, setFilterProject] = useState("");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");

  // Today formatted as YYYY-MM-DD
  const todayStr = new Date().toISOString().split("T")[0];

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingReportId, setEditingReportId] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);

  // Form State
  const initialForm = {
    report_date: todayStr,
    project_id: "",
    work_summary: "",
    tasks_completed: "",
    hours_worked: 8.0,
    achievements: "",
    blockers: "",
    next_day_plan: "",
  };
  const [form, setForm] = useState(initialForm);

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

  // Load Projects for dropdown (assigned to current user)
  const loadProjects = async () => {
    setLoadingProjects(true);
    setProjectLoadError("");
    try {
      let projs = [];
      if (isHr) {
        try {
          const res = await projectService.listProjects({ page_size: 100, status: "ACTIVE" });
          projs = Array.isArray(res) ? res : (res?.items || res?.data || []);
        } catch (hrErr) {
          console.error("HR load projects fallback:", hrErr);
        }
        if (!projs || projs.length === 0) {
          const myProjs = await projectService.getMyProjects();
          projs = Array.isArray(myProjs) ? myProjs : (myProjs?.items || myProjs?.data || []);
        }
      } else {
        const myProjs = await projectService.getMyProjects();
        projs = Array.isArray(myProjs) ? myProjs : (myProjs?.items || myProjs?.data || []);
      }

      // Filter only active projects for new work report submission
      const activeProjs = (projs || []).filter((p) => {
        const st = (typeof p.status === "string" ? p.status : p.status?.value || "").toUpperCase();
        return st === "ACTIVE" || !st;
      });

      setProjects(activeProjs);
    } catch (err) {
      console.error("Load projects error:", err);
      setProjectLoadError("Unable to load your projects. Please try again.");
    } finally {
      setLoadingProjects(false);
    }
  };

  // Load Reports
  const loadReports = async () => {
    setLoading(true);
    try {
      const myData = await workReportService.listMyReports();
      setMyReports(Array.isArray(myData) ? myData : (myData?.reports || myData?.items || []));

      if (isHr) {
        const hrData = await workReportService.listHrReports();
        setEmployeeReports(Array.isArray(hrData) ? hrData : (hrData?.reports || hrData?.items || []));
      }
    } catch (err) {
      console.error("Failed to load work reports:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to load work reports." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
    loadReports();
  }, [isHr]);

  // Open Add modal
  const handleOpenAdd = () => {
    setEditingReportId(null);
    setForm({
      ...initialForm,
      project_id: projects.length === 1 ? String(projects[0].id) : "",
    });
    setShowAddModal(true);
    if (projects.length === 0 && !loadingProjects) {
      loadProjects();
    }
  };

  // Open Edit modal
  const handleOpenEdit = (report) => {
    setEditingReportId(report.id);
    setForm({
      report_date: report.report_date,
      project_id: report.project_id,
      work_summary: report.work_summary || "",
      tasks_completed: report.tasks_completed || "",
      hours_worked: report.hours_worked ?? 8.0,
      achievements: report.achievements || "",
      blockers: report.blockers || "",
      next_day_plan: report.next_day_plan || "",
    });
    setShowAddModal(true);
  };

  // Save Report (Draft or Submit)
  const handleSaveReport = async (submitNow = false) => {
    if (!form.project_id) {
      setNotification({ type: "error", text: "Please select a project." });
      return;
    }
    if (!form.report_date) {
      setNotification({ type: "error", text: "Report date is required." });
      return;
    }
    if (form.report_date > todayStr) {
      setNotification({ type: "error", text: "Report date cannot be a future date." });
      return;
    }
    if (!form.work_summary.trim()) {
      setNotification({ type: "error", text: "Work summary is required." });
      return;
    }
    const hours = parseFloat(form.hours_worked);
    if (isNaN(hours) || hours < 0 || hours > 24) {
      setNotification({ type: "error", text: "Hours worked must be between 0 and 24." });
      return;
    }

    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      const payload = {
        project_id: parseInt(form.project_id),
        report_date: form.report_date,
        work_summary: form.work_summary.trim(),
        tasks_completed: form.tasks_completed?.trim() || null,
        hours_worked: hours,
        achievements: form.achievements?.trim() || null,
        blockers: form.blockers?.trim() || null,
        next_day_plan: form.next_day_plan?.trim() || null,
        status: submitNow ? "SUBMITTED" : "DRAFT",
      };

      if (editingReportId) {
        await workReportService.update(editingReportId, payload);
        if (submitNow) {
          await workReportService.submit(editingReportId);
        }
        setNotification({
          type: "success",
          text: submitNow ? "Daily work report submitted successfully!" : "Work report draft updated.",
        });
      } else {
        const created = await workReportService.create(payload);
        if (submitNow && created?.id && created.status !== "SUBMITTED") {
          await workReportService.submit(created.id);
        }
        setNotification({
          type: "success",
          text: submitNow ? "Daily work report submitted successfully!" : "Work report draft saved.",
        });
      }

      setShowAddModal(false);
      setEditingReportId(null);
      setForm(initialForm);
      await loadReports();
    } catch (err) {
      console.error("Save report error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to save work report." });
    } finally {
      setSubmitting(false);
    }
  };

  // Submit existing Draft directly from list
  const handleSubmitDirect = async (report) => {
    if (!window.confirm(`Submit work report for ${report.report_date}? Once submitted, it cannot be modified.`)) return;
    setSubmitting(true);
    try {
      await workReportService.submit(report.id);
      setNotification({ type: "success", text: "Work report submitted successfully!" });
      await loadReports();
    } catch (err) {
      console.error("Submit report error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to submit work report." });
    } finally {
      setSubmitting(false);
    }
  };

  // Delete Draft
  const handleDeleteDraft = async (report) => {
    if (!window.confirm(`Delete draft report for ${report.report_date}?`)) return;
    setSubmitting(true);
    try {
      await workReportService.delete(report.id);
      setNotification({ type: "success", text: "Draft report deleted." });
      await loadReports();
    } catch (err) {
      console.error("Delete report error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to delete report." });
    } finally {
      setSubmitting(false);
    }
  };

  // Top KPI metric counters for HR (derived directly from real DB records)
  const totalReportsCount = employeeReports.length;
  const submittedTodayCount = employeeReports.filter(
    (r) => r.report_date === todayStr && (r.status === "SUBMITTED" || r.status === "APPROVED")
  ).length;
  const draftReportsCount = employeeReports.filter((r) => r.status === "DRAFT").length;
  const employeesReportedCount = new Set(
    employeeReports.map((r) => r.employee_id || r.employee_code || r.employee_name).filter(Boolean)
  ).size;

  const handleResetFilters = () => {
    setFilterEmployee("");
    setFilterProject("");
    setFilterStartDate("");
    setFilterEndDate("");
    setFilterStatus("ALL");
  };

  // Filter HR employee reports
  const filteredEmployeeReports = employeeReports.filter((r) => {
    if (filterStatus !== "ALL" && r.status !== filterStatus) return false;
    if (filterStartDate && r.report_date < filterStartDate) return false;
    if (filterEndDate && r.report_date > filterEndDate) return false;
    if (filterProject && String(r.project_id) !== String(filterProject)) return false;
    if (filterEmployee) {
      const q = filterEmployee.toLowerCase().trim();
      const matchName = r.employee_name?.toLowerCase().includes(q);
      const matchCode = r.employee_code?.toLowerCase().includes(q);
      const matchSummary = r.work_summary?.toLowerCase().includes(q);
      const matchProj = r.project_name?.toLowerCase().includes(q);
      if (!matchName && !matchCode && !matchSummary && !matchProj) return false;
    }
    return true;
  });

  const getDashboardPath = () => (isHr ? "/hr/dashboard" : "/employee/dashboard");

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
              <h2>Work Reports</h2>
              <span>{isHr ? "Workforce Daily Progress & Output Deck" : "Daily Activity & Milestone Tracking"}</span>
            </div>
          </div>

          <div className="module-header-right">
            <button className="module-action-btn primary" onClick={handleOpenAdd}>
              <Plus size={16} />
              <span>Add Daily Report</span>
            </button>
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

        {/* HR KPI METRIC SUMMARY CARDS (DYNAMIC - FROM DATABASE) */}
        {isHr && (
          <div style={{ marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a", margin: "0 0 2px 0" }}>
                  Workforce Daily Progress & Output
                </h3>
                <span style={{ fontSize: "12px", color: "#64748b" }}>
                  Real-time company-wide daily work report metrics and tracking
                </span>
              </div>
            </div>

            <div className="module-kpi-grid">
              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <FileText size={16} color="#047857" /> Total Reports
                </div>
                <div className="module-kpi-value">{totalReportsCount}</div>
                <div className="module-kpi-sub">Total company reports logged</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <CheckCircle2 size={16} color="#16a34a" /> Submitted Today
                </div>
                <div className="module-kpi-value" style={{ color: "#16a34a" }}>{submittedTodayCount}</div>
                <div className="module-kpi-sub">Submissions for {todayStr}</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <Clock size={16} color="#d97706" /> Draft Reports
                </div>
                <div className="module-kpi-value" style={{ color: "#d97706" }}>{draftReportsCount}</div>
                <div className="module-kpi-sub">Incomplete / draft status</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <Users size={16} color="#7c3aed" /> Employees Reported
                </div>
                <div className="module-kpi-value" style={{ color: "#7c3aed" }}>{employeesReportedCount}</div>
                <div className="module-kpi-sub">Unique active contributors</div>
              </div>
            </div>
          </div>
        )}

        {/* REPORT MANAGEMENT TABS */}
        {isHr && (
          <div style={{ marginBottom: "16px" }}>
            <div style={{ fontSize: "12px", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b", marginBottom: "8px" }}>
              Report Management
            </div>
            <div className="module-tabs-nav">
              <button
                className={`module-tab-btn ${activeTab === "employee-reports" ? "active" : ""}`}
                onClick={() => setActiveTab("employee-reports")}
              >
                <Briefcase size={16} /> Employee Reports ({employeeReports.length})
              </button>
              <button
                className={`module-tab-btn ${activeTab === "my-reports" ? "active" : ""}`}
                onClick={() => setActiveTab("my-reports")}
              >
                <User size={16} /> My Reports ({myReports.length})
              </button>
            </div>
          </div>
        )}

        {/* HR Filters (Only on Employee Reports tab) */}
        {isHr && activeTab === "employee-reports" && (
          <div
            style={{
              background: "#ffffff",
              padding: "20px",
              borderRadius: "12px",
              border: "1px solid #e2e8f0",
              marginBottom: "20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
            }}
          >
            <div className="work-reports-filter-grid">
              {/* Search Employee / Report */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Search Employee / Report
                </label>
                <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                  <Search size={15} style={{ position: "absolute", left: "12px", color: "#94a3b8" }} />
                  <input
                    type="text"
                    placeholder="Search employee name or report..."
                    value={filterEmployee}
                    onChange={(e) => setFilterEmployee(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px 12px 8px 36px",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      fontSize: "13px",
                      outline: "none",
                      height: "40px",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              </div>

              {/* All Projects */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Project
                </label>
                <select
                  value={filterProject}
                  onChange={(e) => setFilterProject(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    outline: "none",
                    background: "#ffffff",
                    height: "40px",
                    boxSizing: "border-box",
                  }}
                >
                  <option value="">All Projects</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.project_name || p.name || p.title || `Project #${p.id}`}</option>
                  ))}
                </select>
              </div>

              {/* Start Date */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Start Date
                </label>
                <input
                  type="date"
                  value={filterStartDate}
                  onChange={(e) => setFilterStartDate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    outline: "none",
                    height: "40px",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* End Date */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  End Date
                </label>
                <input
                  type="date"
                  value={filterEndDate}
                  onChange={(e) => setFilterEndDate(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    outline: "none",
                    height: "40px",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Status */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Status
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    fontSize: "13px",
                    outline: "none",
                    background: "#ffffff",
                    height: "40px",
                    boxSizing: "border-box",
                  }}
                >
                  <option value="ALL">All Statuses</option>
                  <option value="SUBMITTED">Submitted</option>
                  <option value="DRAFT">Draft</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px", flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn-secondary"
                style={{ padding: "8px 16px", fontSize: "13px" }}
                onClick={handleResetFilters}
              >
                Reset
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{ padding: "8px 18px", fontSize: "13px" }}
                onClick={() => {}}
              >
                <Filter size={14} /> Filter Reports
              </button>
            </div>
          </div>
        )}

        {/* TAB 1: EMPLOYEE REPORTS (HR VIEW) */}
        {isHr && activeTab === "employee-reports" && (
          <div className="module-table-container">
            {loading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
                <Loader2 size={24} className="spin-animation" />
                <span>Loading employee reports...</span>
              </div>
            ) : filteredEmployeeReports.length === 0 ? (
              <div className="module-empty-box">
                <FileChartColumn size={40} className="module-empty-icon" />
                <div className="module-empty-title">No employee reports found</div>
                <div className="module-empty-desc">
                  {filterEmployee || filterProject || filterStartDate || filterEndDate || filterStatus !== "ALL"
                    ? "Try adjusting the filters above to find matching submissions."
                    : "No employee work reports have been recorded yet."}
                </div>
              </div>
            ) : (
              <table className="module-table">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Project</th>
                    <th style={{ width: "130px" }}>Date</th>
                    <th style={{ width: "90px" }}>Hours</th>
                    <th style={{ width: "120px" }}>Status</th>
                    <th>Work Summary</th>
                    <th style={{ width: "100px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployeeReports.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: "#0f172a", fontSize: "14px" }}>
                          {r.employee_name || "Employee"}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748b" }}>
                          {r.employee_code || `ID: ${r.employee_id}`}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 500, color: "#334155" }}>
                          {r.project_name || `Project #${r.project_id}`}
                        </span>
                      </td>
                      <td style={{ fontSize: "13px", color: "#475569" }}>
                        {r.report_date}
                      </td>
                      <td style={{ fontWeight: 600, color: "#0f172a" }}>
                        {r.hours_worked}h
                      </td>
                      <td>
                        <span className={`module-status-badge ${r.status}`}>
                          {r.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ maxWidth: "340px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: "13px", color: "#475569" }}>
                          {r.work_summary}
                        </div>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="module-action-btn secondary"
                          style={{ padding: "5px 10px", fontSize: "12px" }}
                          onClick={() => setSelectedReport(r)}
                        >
                          <Eye size={13} /> View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* TAB 2: MY REPORTS (BOTH HR & EMPLOYEES) */}
        {(!isHr || activeTab === "my-reports") && (
          <div className="module-table-container">
            {loading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
                <Loader2 size={24} className="spin-animation" />
                <span>Loading your work reports...</span>
              </div>
            ) : myReports.length === 0 ? (
              <div className="module-empty-box">
                <FileChartColumn size={40} className="module-empty-icon" />
                <div className="module-empty-title">No daily reports recorded</div>
                <div className="module-empty-desc">
                  Start logging your daily work accomplishments, tasks completed, and hours worked.
                </div>
                <button className="module-action-btn primary" onClick={handleOpenAdd}>
                  <Plus size={15} /> Add Today's Report
                </button>
              </div>
            ) : (
              <table className="module-table">
                <thead>
                  <tr>
                    <th style={{ width: "130px" }}>Date</th>
                    <th>Project</th>
                    <th>Work Summary</th>
                    <th style={{ width: "90px" }}>Hours</th>
                    <th style={{ width: "120px" }}>Status</th>
                    <th style={{ width: "200px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {myReports.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600, color: "#0f172a", fontSize: "13px" }}>
                        {r.report_date}
                      </td>
                      <td>
                        <span style={{ fontWeight: 500, color: "#334155" }}>
                          {r.project_name || `Project #${r.project_id}`}
                        </span>
                      </td>
                      <td>
                        <div style={{ maxWidth: "380px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: "13px", color: "#475569" }}>
                          {r.work_summary}
                        </div>
                      </td>
                      <td style={{ fontWeight: 600, color: "#0f172a" }}>
                        {r.hours_worked}h
                      </td>
                      <td>
                        <span className={`module-status-badge ${r.status}`}>
                          {r.status}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "6px" }}>
                          <button
                            className="module-action-btn secondary"
                            style={{ padding: "5px 10px", fontSize: "12px" }}
                            onClick={() => setSelectedReport(r)}
                            title="View Report Details"
                          >
                            <Eye size={13} /> View
                          </button>

                          {r.status === "DRAFT" && (
                            <>
                              <button
                                className="module-action-btn secondary"
                                style={{ padding: "5px 10px", fontSize: "12px" }}
                                onClick={() => handleOpenEdit(r)}
                                title="Edit Draft"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                className="module-action-btn primary"
                                style={{ padding: "5px 10px", fontSize: "12px" }}
                                onClick={() => handleSubmitDirect(r)}
                                disabled={submitting}
                                title="Submit Report"
                              >
                                <Send size={13} />
                              </button>
                              <button
                                className="module-action-btn secondary"
                                style={{ padding: "5px 10px", fontSize: "12px", color: "#ef4444" }}
                                onClick={() => handleDeleteDraft(r)}
                                disabled={submitting}
                                title="Delete Draft"
                              >
                                <Trash2 size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>

      {/* ADD / EDIT REPORT MODAL */}
      {showAddModal && (
        <div className="module-modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="module-modal-dialog modal-work-report" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <FileChartColumn size={20} color="#047857" />
                  <span>{editingReportId ? "Edit Work Report Draft" : "Add Daily Work Report"}</span>
                </h3>
                <p className="module-modal-subtitle">
                  Submit your work completed for the selected project and date.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowAddModal(false)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              <div className="form-grid">
                <div className="form-section-header">
                  Work Details
                </div>

                <div className="form-field">
                  <label>
                    Report Date <span className="required-star">*</span>
                  </label>
                  <input
                    type="date"
                    max={todayStr}
                    value={form.report_date}
                    onChange={(e) => setForm({ ...form, report_date: e.target.value })}
                    required
                  />
                </div>

                <div className="form-field">
                  <label>
                    Project <span className="required-star">*</span>
                  </label>
                  <select
                    value={form.project_id}
                    onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                    required
                    disabled={loadingProjects}
                  >
                    {loadingProjects ? (
                      <option value="" disabled>Loading projects...</option>
                    ) : projectLoadError ? (
                      <option value="" disabled>Unable to load your projects. Please try again.</option>
                    ) : projects.length === 0 ? (
                      <option value="" disabled>No assigned projects available</option>
                    ) : (
                      <>
                        <option value="">Select Project</option>
                        {projects.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.project_name || p.name || p.title || `Project #${p.id}`}
                          </option>
                        ))}
                      </>
                    )}
                  </select>
                  {projectLoadError && (
                    <div style={{ color: "#ef4444", fontSize: "12px", marginTop: "4px" }}>
                      {projectLoadError}
                    </div>
                  )}
                  {(() => {
                    const selProj = projects.find((p) => String(p.id) === String(form.project_id));
                    if (selProj?.my_role && selProj.my_role !== "Role not assigned") {
                      return (
                        <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>
                          Assigned Role: <strong style={{ color: "#334155" }}>{selProj.my_role}</strong>
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>

                <div className="form-field">
                  <label>
                    Hours Worked (0 - 24) <span className="required-star">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="24"
                    placeholder="e.g. 8"
                    value={form.hours_worked}
                    onChange={(e) => setForm({ ...form, hours_worked: e.target.value })}
                    required
                  />
                </div>

                <div className="form-field">
                  <label>
                    Submission Type
                  </label>
                  <div style={{ display: "flex", alignItems: "center", height: "42px", padding: "0 12px", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", fontSize: "13px", color: "#475569", fontWeight: 600 }}>
                    {editingReportId ? "Draft Modification" : "Daily Activity Report (Draft / Submit)"}
                  </div>
                </div>

                <div className="form-section-header">
                  Work Summary & Tasks
                </div>

                <div className="form-field form-field-full">
                  <label>
                    Work Summary <span className="required-star">*</span>
                  </label>
                  <textarea
                    placeholder="High-level summary of work performed today..."
                    value={form.work_summary}
                    onChange={(e) => setForm({ ...form, work_summary: e.target.value })}
                    required
                  />
                </div>

                <div className="form-field form-field-full">
                  <label>
                    Tasks Completed <span className="optional-tag">(Optional)</span>
                  </label>
                  <textarea
                    placeholder="Bullet points or details of tasks accomplished..."
                    value={form.tasks_completed}
                    onChange={(e) => setForm({ ...form, tasks_completed: e.target.value })}
                  />
                </div>

                <div className="form-section-header">
                  Achievements & Blockers
                </div>

                <div className="form-field">
                  <label>
                    Achievements <span className="optional-tag">(Optional)</span>
                  </label>
                  <textarea
                    placeholder="Milestones reached or key achievements..."
                    value={form.achievements}
                    onChange={(e) => setForm({ ...form, achievements: e.target.value })}
                  />
                </div>

                <div className="form-field">
                  <label>
                    Blockers / Impediments <span className="optional-tag">(Optional)</span>
                  </label>
                  <textarea
                    placeholder="Any blockers or external dependencies..."
                    value={form.blockers}
                    onChange={(e) => setForm({ ...form, blockers: e.target.value })}
                  />
                </div>

                <div className="form-section-header">
                  Forward Planning
                </div>

                <div className="form-field form-field-full">
                  <label>
                    Next Day Plan <span className="optional-tag">(Optional)</span>
                  </label>
                  <textarea
                    placeholder="Planned agenda and tasks for the next working day..."
                    value={form.next_day_plan}
                    onChange={(e) => setForm({ ...form, next_day_plan: e.target.value })}
                  />
                </div>
              </div>
            </div>

            <div className="module-modal-footer">
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setShowAddModal(false)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => handleSaveReport(false)}
                disabled={submitting}
              >
                {submitting ? <Loader2 size={14} className="spin-animation" /> : "Save Draft"}
              </button>
              <button
                type="button"
                className="module-action-btn primary"
                onClick={() => handleSaveReport(true)}
                disabled={submitting}
              >
                {submitting ? <Loader2 size={14} className="spin-animation" /> : <><Send size={14} /> Submit Report</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VIEW REPORT DETAILS MODAL */}
      {selectedReport && (
        <div className="module-modal-overlay" onClick={() => setSelectedReport(null)}>
          <div className="module-modal-dialog modal-work-report" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <FileChartColumn size={20} color="#047857" />
                  <span>Work Report: {selectedReport.report_date}</span>
                </h3>
                <p className="module-modal-subtitle">
                  Detailed inspection of submitted daily work log
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedReport(null)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              <div className="info-grid">
                {selectedReport.employee_name && (
                  <div className="info-cell">
                    <span className="info-cell-label">Employee</span>
                    <div className="info-cell-value">{selectedReport.employee_name} ({selectedReport.employee_code})</div>
                  </div>
                )}
                <div className="info-cell">
                  <span className="info-cell-label">Project</span>
                  <div className="info-cell-value">{selectedReport.project_name || `Project #${selectedReport.project_id}`}</div>
                </div>
                <div className="info-cell">
                  <span className="info-cell-label">Hours Worked</span>
                  <div className="info-cell-value">{selectedReport.hours_worked} hours</div>
                </div>
                <div className="info-cell">
                  <span className="info-cell-label">Current Status</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedReport.status.toLowerCase()}`}>
                      {selectedReport.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="form-section-header">
                Work Summary
              </div>
              <div className="detail-content-box">
                {selectedReport.work_summary || "—"}
              </div>

              {selectedReport.tasks_completed && (
                <>
                  <div className="form-section-header">
                    Tasks Completed
                  </div>
                  <div className="detail-content-box">
                    {selectedReport.tasks_completed}
                  </div>
                </>
              )}

              {(selectedReport.achievements || selectedReport.blockers) && (
                <div className="form-grid">
                  {selectedReport.achievements && (
                    <div className="form-field">
                      <div className="form-section-header" style={{ marginTop: 0 }}>
                        Achievements
                      </div>
                      <div className="detail-content-box" style={{ marginTop: "8px" }}>
                        {selectedReport.achievements}
                      </div>
                    </div>
                  )}

                  {selectedReport.blockers && (
                    <div className="form-field">
                      <div className="form-section-header" style={{ marginTop: 0, color: "#dc2626" }}>
                        Blockers / Impediments
                      </div>
                      <div className="detail-content-box" style={{ marginTop: "8px", background: "#fef2f2", borderColor: "#fecaca", color: "#991b1b" }}>
                        {selectedReport.blockers}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedReport.next_day_plan && (
                <>
                  <div className="form-section-header">
                    Next Day Plan
                  </div>
                  <div className="detail-content-box">
                    {selectedReport.next_day_plan}
                  </div>
                </>
              )}
            </div>

            <div className="module-modal-footer">
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setSelectedReport(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
