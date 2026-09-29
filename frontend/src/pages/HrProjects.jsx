import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { 
  FolderKanban, 
  Plus, 
  ArrowLeft, 
  Search, 
  Calendar, 
  CheckCircle2, 
  AlertCircle,
  X,
  Edit2,
  Info,
  Clock,
  Loader2,
  Settings,
  Sliders,
  TrendingUp,
  AlertTriangle,
  Users,
  User,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { projectService, projectRoleService } from "../services/api";
import "../styles/Projects.css";

export default function HrProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [notification, setNotification] = useState({ type: "", text: "" });

  // 5 HR Project Dashboard Metrics
  const [metrics, setMetrics] = useState({
    total_projects: 0,
    active_projects: 0,
    completed_projects: 0,
    on_hold_projects: 0,
    overdue_projects: 0,
  });

  // Dedicated Modals
  const [createModal, setCreateModal] = useState(false);
  const [detailsModal, setDetailsModal] = useState(null); // READ-ONLY details overview
  const [detailsRoles, setDetailsRoles] = useState([]);   // Roles & assigned employees for details modal
  const [loadingDetailsRoles, setLoadingDetailsRoles] = useState(false);
  const [editModal, setEditModal] = useState(null);       // Edit Project modal (Sections 1, 2, 5)

  // State inside Edit Project Modal
  const [editForm, setEditForm] = useState({
    id: null,
    project_code: "",
    project_name: "",
    description: "",
    status: "ACTIVE",
    priority: "MEDIUM",
    progress_percentage: 0,
    client_name: "",
    start_date: "",
    expected_end_date: "",
  });

  const [loadingEditData, setLoadingEditData] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState(null);

  // Create Project Form
  const [createForm, setCreateForm] = useState({
    project_code: "",
    project_name: "",
    description: "",
    status: "ACTIVE",
    priority: "MEDIUM",
    client_name: "",
    start_date: new Date().toISOString().split("T")[0],
    expected_end_date: "",
  });
  const [createError, setCreateError] = useState("");
  const [submittingCreate, setSubmittingCreate] = useState(false);

  // ========================================================
  // LOAD PROJECTS & METRICS
  // ========================================================
  const loadProjects = async () => {
    setLoading(true);
    try {
      const [data, metricsRes] = await Promise.all([
        projectService.listProjects({ page_size: 100 }),
        projectService.getMetrics().catch(() => null),
      ]);

      const items = data.items || [];
      setProjects(items);

      if (metricsRes) {
        setMetrics(metricsRes);
      } else {
        // Fallback calculations
        setMetrics({
          total_projects: items.length,
          active_projects: items.filter((p) => p.status === "ACTIVE").length,
          completed_projects: items.filter((p) => p.status === "COMPLETED").length,
          on_hold_projects: items.filter((p) => p.status === "ON_HOLD").length,
          overdue_projects: items.filter((p) => p.is_overdue).length,
        });
      }
    } catch (err) {
      console.error("Failed to load projects:", err);
      setNotification({ type: "error", text: "Failed to load project records." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Filter projects by Status, Priority, and Search
  const filteredProjects = projects.filter((p) => {
    const matchesStatus =
      activeFilter === "ALL" ||
      (activeFilter === "ACTIVE" && p.status === "ACTIVE") ||
      (activeFilter === "COMPLETED" && p.status === "COMPLETED") ||
      (activeFilter === "ON_HOLD" && p.status === "ON_HOLD") ||
      (activeFilter === "PLANNING" && (p.status === "PLANNING" || p.status === "PLANNED"));

    const matchesPriority =
      priorityFilter === "ALL" ||
      (p.priority && p.priority.toUpperCase() === priorityFilter);

    const matchesSearch =
      !searchQuery ||
      p.project_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.project_code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.client_name && p.client_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesStatus && matchesPriority && matchesSearch;
  });

  // ========================================================
  // REFRESH EDIT MODAL DATA
  // ========================================================
  const refreshEditProjectData = async (projectId) => {
    try {
      const proj = await projectService.getProject(projectId);
      setEditModal(proj);
      setEditForm({
        id: proj.id,
        project_code: proj.project_code,
        project_name: proj.project_name,
        description: proj.description || "",
        status: proj.status,
        priority: proj.priority,
        progress_percentage: proj.progress_percentage || 0,
        client_name: proj.client_name || "",
        start_date: proj.start_date,
        expected_end_date: proj.expected_end_date,
      });
      loadProjects(); // refresh main list and metrics
      return proj;
    } catch (err) {
      console.error("Error refreshing edit data:", err);
      return null;
    }
  };

  // ========================================================
  // 1. OPEN READ-ONLY DETAILS MODAL & LOAD REAL ROLES + TEAM
  // ========================================================
  const loadDetailsRoles = async (projectId) => {
    if (!projectId) return;
    setLoadingDetailsRoles(true);
    try {
      const rolesData = await projectRoleService.listRoles({ project_id: projectId });
      const rolesList = Array.isArray(rolesData) ? rolesData : (rolesData?.items || []);

      // Filter to ensure only roles for this project are included
      const scopedRoles = rolesList.filter(
        (r) => Number(r.project_id) === Number(projectId)
      );

      // For every role, retrieve actively assigned employees
      const rolesWithAssignments = await Promise.all(
        scopedRoles.map(async (role) => {
          try {
            const employees = await projectRoleService.getAssignedEmployees(role.id, projectId);
            const empList = Array.isArray(employees)
              ? employees
              : (employees?.assignments || employees?.items || []);
            return {
              ...role,
              assigned_employees: empList,
            };
          } catch (err) {
            console.error(`Failed to load assignments for role ${role.id}:`, err);
            return {
              ...role,
              assigned_employees: [],
            };
          }
        })
      );

      setDetailsRoles(rolesWithAssignments);
    } catch (roleErr) {
      console.error("Failed to load project roles:", roleErr);
      setDetailsRoles([]);
    } finally {
      setLoadingDetailsRoles(false);
    }
  };

  const handleOpenDetails = async (projectId) => {
    try {
      const proj = await projectService.getProject(projectId);
      setDetailsModal(proj);
      setDetailsRoles([]);
      loadDetailsRoles(projectId);
    } catch (err) {
      setNotification({ type: "error", text: "Could not open project details." });
    }
  };

  // ========================================================
  // 2. OPEN EDIT PROJECT MODAL (Sections 1, 2, 5)
  // ========================================================
  const handleOpenEdit = async (projectOrId) => {
    const projectId = typeof projectOrId === "object" ? projectOrId.id : projectOrId;
    setLoadingEditData(true);
    setEditError(null);
    try {
      const proj = await projectService.getProject(projectId);
      setEditModal(proj);
      setEditForm({
        id: proj.id,
        project_code: proj.project_code,
        project_name: proj.project_name,
        description: proj.description || "",
        status: proj.status,
        priority: proj.priority,
        progress_percentage: proj.progress_percentage || 0,
        client_name: proj.client_name || "",
        start_date: proj.start_date,
        expected_end_date: proj.expected_end_date,
      });
    } catch (err) {
      console.error("Could not load project for editing:", err);
      setNotification({ type: "error", text: "Could not load project for editing." });
    } finally {
      setLoadingEditData(false);
    }
  };

  // ========================================================
  // SAVE EDIT PROJECT (Sections 1, 2, 5)
  // ========================================================
  const handleSaveEditProject = async (e) => {
    if (e) e.preventDefault();
    if (!editModal) return;

    if (!editForm.project_name.trim()) {
      setEditError("Project Name is required.");
      return;
    }
    if (!editForm.start_date) {
      setEditError("Start Date is required.");
      return;
    }
    if (editForm.expected_end_date && editForm.expected_end_date < editForm.start_date) {
      setEditError("Expected End Date cannot be before Start Date.");
      return;
    }

    setSavingEdit(true);
    setEditError(null);
    try {
      const progressVal = parseInt(editForm.progress_percentage, 10) || 0;

      // Update core project info & dates
      await projectService.updateProject(editModal.id, {
        project_name: editForm.project_name.trim(),
        name: editForm.project_name.trim(),
        description: editForm.description.trim() || undefined,
        priority: editForm.priority,
        client_name: editForm.client_name.trim() || undefined,
        start_date: editForm.start_date,
        expected_end_date: editForm.expected_end_date || undefined,
        end_date: editForm.expected_end_date || undefined,
      });

      // Update progress if changed
      if (progressVal !== (editModal.progress_percentage || 0)) {
        await projectService.updateProjectProgress(editModal.id, progressVal);
      }

      // Update status if changed
      if (editForm.status !== editModal.status) {
        await projectService.updateProjectStatus(editModal.id, editForm.status);
      }

      setNotification({
        type: "success",
        text: `Project "${editForm.project_name}" updated successfully.`,
      });
      await refreshEditProjectData(editModal.id);
      setEditModal(null);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || "Failed to update project.";
      setEditError(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setSavingEdit(false);
    }
  };

  // ========================================================
  // Helper to format/normalize date string to ISO YYYY-MM-DD
  const formatToISODate = (val) => {
    if (!val || typeof val !== "string") return undefined;
    const trimmed = val.trim();
    if (!trimmed) return undefined;
    const ddmmyyyy = trimmed.match(/^(\d{2})[-/](\d{2})[-/](\d{4})$/);
    if (ddmmyyyy) {
      return `${ddmmyyyy[3]}-${ddmmyyyy[2]}-${ddmmyyyy[1]}`;
    }
    return trimmed;
  };

  // ========================================================
  // CREATE PROJECT (Direct API with No Roles Required)
  // ========================================================
  const handleCreateProject = async (e) => {
    if (e) e.preventDefault();
    if (submittingCreate) return;

    if (!createForm.project_name.trim()) {
      setCreateError("Project Name is required.");
      return;
    }
    if (!createForm.start_date) {
      setCreateError("Start Date is required.");
      return;
    }

    const isoStartDate = formatToISODate(createForm.start_date);
    const isoEndDate = formatToISODate(createForm.expected_end_date);

    if (isoEndDate && isoStartDate && isoEndDate < isoStartDate) {
      setCreateError("Expected End Date cannot be before Start Date.");
      return;
    }

    setSubmittingCreate(true);
    setCreateError("");
    try {
      const payload = {
        name: createForm.project_name.trim(),
        project_name: createForm.project_name.trim(),
        project_code: createForm.project_code.trim() ? createForm.project_code.trim().toUpperCase() : undefined,
        status: createForm.status || "ACTIVE",
        priority: createForm.priority || "MEDIUM",
        client_name: createForm.client_name.trim() || undefined,
        start_date: isoStartDate,
        expected_end_date: isoEndDate || undefined,
        end_date: isoEndDate || undefined,
        description: createForm.description.trim() || undefined,
      };

      const created = await projectService.createProject(payload);
      setNotification({
        type: "success",
        text: `Project "${created.project_name || created.name}" (${created.project_code}) created successfully.`,
      });
      setCreateModal(false);
      setCreateForm({
        project_code: "",
        project_name: "",
        description: "",
        status: "ACTIVE",
        priority: "MEDIUM",
        client_name: "",
        start_date: new Date().toISOString().split("T")[0],
        expected_end_date: "",
      });
      setCreateError("");
      await loadProjects();
    } catch (err) {
      console.error("Create project error:", err);
      let detail = "Unable to create project. Please check the entered information and try again.";
      if (err.response) {
        if (err.response.status === 401) {
          detail = "Your session has expired. Please log in again.";
        } else if (err.response.status === 403) {
          detail = "You do not have permission to create projects.";
        } else if (err.response.status === 409 || (err.response.data?.detail && String(err.response.data.detail).toLowerCase().includes("already exists"))) {
          detail = err.response.data.detail || "Project code already exists.";
        } else if (err.response.data?.detail) {
          const backendDetail = err.response.data.detail;
          if (Array.isArray(backendDetail)) {
            detail = backendDetail.map((d) => d.msg || d.message).join(", ");
          } else if (typeof backendDetail === "string") {
            detail = backendDetail;
          } else {
            detail = JSON.stringify(backendDetail);
          }
        } else if (err.response.status >= 500) {
          detail = "Unable to create the project due to a server error. Please try again.";
        }
      } else if (err.request) {
        detail = "Unable to connect to the server. Please verify your connection and try again.";
      } else if (err.message && err.message !== "Network Error") {
        detail = err.message;
      }
      setCreateError(detail);
    } finally {
      setSubmittingCreate(false);
    }
  };

  return (
    <div className="prj-page-wrapper">
      {/* ================= HEADER BAR ================= */}
      <header className="prj-header-bar">
        <div className="prj-header-container">
          <div className="prj-header-left">
            <Link to="/hr/dashboard" className="prj-back-btn">
              <ArrowLeft size={16} />
              <span>HR Dashboard</span>
            </Link>
            <div className="prj-header-meta">
              <h2>Enterprise Projects</h2>
              <span>Mediatize HRMS • Sprint Allocations & Delivery Governance</span>
            </div>
          </div>
          <div className="prj-header-actions">
            <button className="prj-primary-btn" onClick={() => setCreateModal(true)}>
              <Plus size={16} />
              <span>Create Project</span>
            </button>
          </div>
        </div>
      </header>

      {/* ================= MAIN CONTENT ================= */}
      <main className="prj-content-container project-page-container">
        {notification.text && (
          <div
            style={{
              marginBottom: "16px",
              padding: "12px 16px",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: notification.type === "success" ? "#ecfdf5" : "#fef2f2",
              color: notification.type === "success" ? "#065f46" : "#991b1b",
              border: `1px solid ${notification.type === "success" ? "#a7f3d0" : "#fecaca"}`,
              fontSize: "13px",
              fontWeight: "600",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {notification.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
              <span>{notification.text}</span>
            </div>
            <button
              onClick={() => setNotification({ type: "", text: "" })}
              style={{ background: "transparent", border: "none", cursor: "pointer", color: "inherit" }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* 5 HR METRICS / KPI GRID */}
        <section className="project-kpi-grid prj-metrics-grid">
          {/* 1. Total Projects */}
          <div className="project-kpi-card prj-metric-card">
            <div className="kpi-icon-badge total">
              <FolderKanban size={20} />
            </div>
            <span className="kpi-label">Total Projects</span>
            <div className="kpi-value">{metrics.total_projects}</div>
          </div>

          {/* 2. Active Projects */}
          <div className="project-kpi-card prj-metric-card">
            <div className="kpi-icon-badge active">
              <CheckCircle2 size={20} />
            </div>
            <span className="kpi-label">Active Projects</span>
            <div className="kpi-value text-emerald">{metrics.active_projects}</div>
          </div>

          {/* 3. Completed */}
          <div className="project-kpi-card prj-metric-card">
            <div className="kpi-icon-badge completed">
              <Calendar size={20} />
            </div>
            <span className="kpi-label">Completed</span>
            <div className="kpi-value">{metrics.completed_projects}</div>
          </div>

          {/* 4. On Hold */}
          <div className="project-kpi-card prj-metric-card">
            <div className="kpi-icon-badge onhold">
              <Clock size={20} />
            </div>
            <span className="kpi-label">On Hold</span>
            <div className="kpi-value text-amber">{metrics.on_hold_projects}</div>
          </div>

          {/* 5. Overdue Projects */}
          <div className="project-kpi-card prj-metric-card">
            <div className="kpi-icon-badge overdue">
              <AlertCircle size={20} />
            </div>
            <span className="kpi-label">Overdue Projects</span>
            <div className="kpi-value text-rose">{metrics.overdue_projects}</div>
          </div>
        </section>

        {/* FILTER & SEARCH TOOLBAR (Status + Priority + Search) */}
        <section className="prj-toolbar-card">
          <div className="prj-filters-group" style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <button
              className={`prj-filter-btn ${activeFilter === "ALL" ? "active" : ""}`}
              onClick={() => setActiveFilter("ALL")}
            >
              All <span className="counter">{projects.length}</span>
            </button>
            <button
              className={`prj-filter-btn ${activeFilter === "ACTIVE" ? "active" : ""}`}
              onClick={() => setActiveFilter("ACTIVE")}
            >
              Active <span className="counter">{metrics.active_projects}</span>
            </button>
            <button
              className={`prj-filter-btn ${activeFilter === "COMPLETED" ? "active" : ""}`}
              onClick={() => setActiveFilter("COMPLETED")}
            >
              Completed <span className="counter">{metrics.completed_projects}</span>
            </button>
            <button
              className={`prj-filter-btn ${activeFilter === "ON_HOLD" ? "active" : ""}`}
              onClick={() => setActiveFilter("ON_HOLD")}
            >
              On Hold <span className="counter">{metrics.on_hold_projects}</span>
            </button>

            {/* Priority Selector */}
            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", marginLeft: "8px" }}>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                style={{
                  padding: "6px 10px",
                  borderRadius: "8px",
                  border: "1px solid #cbd5e1",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  background: "#ffffff",
                  color: "#334155",
                  outline: "none",
                }}
              >
                <option value="ALL">All Priorities</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>

          <div className="prj-search-box">
            <Search size={16} className="prj-search-icon" />
            <input
              type="text"
              placeholder="Search project name, code, client, scope..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="prj-search-input"
            />
          </div>
        </section>

        {/* ================= PROJECT CARDS LIST ================= */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <Loader2 size={36} className="spinner text-emerald" style={{ margin: "0 auto 12px auto" }} />
            <p style={{ color: "#64748b", fontSize: "14px", fontWeight: "500" }}>Loading project directory...</p>
          </div>
        ) : filteredProjects.length > 0 ? (
          <div className="prj-cards-grid">
            {filteredProjects.map((p) => {
              const progressVal = Math.min(100, Math.max(0, p.progress_percentage || 0));
              return (
                <article key={p.id} className="prj-card">
                  <div>
                    <div className="prj-card-header">
                      <div className="prj-card-title-group">
                        <span className="prj-code-badge">{p.project_code}</span>
                        <h3>{p.project_name}</h3>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                        {p.priority && (
                          <span className={`prj-priority-pill ${p.priority.toLowerCase()}`}>
                            {p.priority}
                          </span>
                        )}
                        <span className={`prj-status-pill ${p.status.toLowerCase()}`}>
                          <span className="dot" />
                          {p.status}
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar (0-100%) */}
                    <div className="prj-progress-wrap" style={{ margin: "12px 0 10px 0" }}>
                      <div className="prj-progress-header">
                        <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <TrendingUp size={12} color="#047857" /> Sprint Progress
                        </span>
                        <span className="prj-progress-val">{progressVal}%</span>
                      </div>
                      <div className="prj-progress-track">
                        <div
                          className={`prj-progress-fill ${progressVal === 100 ? "completed" : ""}`}
                          style={{ width: `${progressVal}%` }}
                        />
                      </div>
                    </div>

                    {/* Overdue alert if applicable */}
                    {p.is_overdue && p.status !== "COMPLETED" && (
                      <div
                        style={{
                          marginBottom: "8px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          color: "#dc2626",
                          background: "#fef2f2",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        <AlertTriangle size={12} /> Target delivery date has passed
                      </div>
                    )}

                    <p className="prj-card-desc">
                      {p.description || "Active production initiative within the Mediatize enterprise ecosystem."}
                    </p>

                    <div className="prj-card-meta-list">
                      <div className="prj-card-meta-item">
                        <span>Team Allocation:</span>
                        <strong>{p.team_members_count || 0} Team Members</strong>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Sprint Window:</span>
                        <strong>{p.start_date} to {p.expected_end_date}</strong>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Client / Stakeholder:</span>
                        <strong>{p.client_name || "Mediatize"}</strong>
                      </div>
                    </div>
                  </div>

                  {/* ONLY TWO ACTION BUTTONS PER REQUIREMENT: [ Details ] [ Edit ] */}
                  <div className="prj-card-actions">
                    <button
                      className="prj-btn-ghost"
                      onClick={() => handleOpenDetails(p.id)}
                      title="View read-only project details"
                    >
                      <Info size={14} />
                      <span>Details</span>
                    </button>

                    <button
                      className="prj-btn-primary-sm"
                      onClick={() => handleOpenEdit(p)}
                      title="Open complete project editing interface"
                    >
                      <Edit2 size={14} />
                      <span>Edit</span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="prj-empty-box" style={{ background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
            <FolderKanban size={48} color="#047857" style={{ margin: "0 auto 12px auto" }} />
            <h4>No Projects Found</h4>
            <p>
              {searchQuery || priorityFilter !== "ALL" || activeFilter !== "ALL"
                ? "No projects matched your active filters or search criteria. Adjust filters or register a new project."
                : "No projects registered in this category yet."}
            </p>
            <button
              className="prj-primary-btn"
              onClick={() => setCreateModal(true)}
              style={{ marginTop: "16px" }}
            >
              <Plus size={16} /> Create Project
            </button>
          </div>
        )}
      </main>

      {/* ========================================================
          MODAL 1: READ-ONLY PROJECT DETAILS MODAL
          ======================================================== */}
      {detailsModal && (
        <div className="prj-modal-overlay" onClick={() => setDetailsModal(null)}>
          <div className="prj-modal-card large" onClick={(e) => e.stopPropagation()}>
            <div className="prj-modal-header">
              <div>
                <h3>Project Details</h3>
                <p>{detailsModal.project_code} • {detailsModal.project_name}</p>
              </div>
              <button className="prj-modal-close" onClick={() => setDetailsModal(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="prj-modal-body">
              {/* Progress Summary Banner */}
              <div
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  padding: "16px 20px",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <TrendingUp size={16} color="#047857" />
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>Project Progress</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {detailsModal.priority && (
                      <span className={`prj-priority-pill ${detailsModal.priority.toLowerCase()}`}>
                        {detailsModal.priority} PRIORITY
                      </span>
                    )}
                    <span className="prj-progress-val" style={{ fontSize: "16px", fontWeight: 800, color: "#047857" }}>
                      {detailsModal.progress_percentage || 0}%
                    </span>
                  </div>
                </div>
                <div className="prj-progress-track" style={{ height: "9px" }}>
                  <div
                    className={`prj-progress-fill ${detailsModal.progress_percentage === 100 ? "completed" : ""}`}
                    style={{ width: `${Math.min(100, Math.max(0, detailsModal.progress_percentage || 0))}%` }}
                  />
                </div>
              </div>

              <div className="prj-overview-grid">
                <div className="prj-overview-card">
                  <span className="label">Project Code</span>
                  <span className="value" style={{ color: "#047857", fontWeight: 700 }}>
                    {detailsModal.project_code}
                  </span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Project Name</span>
                  <span className="value">{detailsModal.project_name}</span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Status</span>
                  <span className="value">
                    <span className={`prj-status-pill ${detailsModal.status.toLowerCase()}`}>
                      <span className="dot" /> {detailsModal.status}
                    </span>
                  </span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Priority</span>
                  <span className="value" style={{ fontWeight: 700 }}>
                    {detailsModal.priority || "MEDIUM"}
                  </span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Client Name</span>
                  <span className="value">{detailsModal.client_name || "Mediatize"}</span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Start Date</span>
                  <span className="value">{detailsModal.start_date}</span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">End Date</span>
                  <span className="value">{detailsModal.expected_end_date || detailsModal.end_date || "—"}</span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Delivery Status</span>
                  <span className="value" style={{ color: detailsModal.is_overdue ? "#dc2626" : "#047857", fontWeight: 600 }}>
                    {detailsModal.is_overdue ? "Overdue Delivery" : "On Schedule"}
                  </span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Created Date</span>
                  <span className="value" style={{ color: "#475569" }}>
                    {detailsModal.created_at ? new Date(detailsModal.created_at).toLocaleDateString() : "—"}
                  </span>
                </div>
                <div className="prj-overview-card">
                  <span className="label">Updated Date</span>
                  <span className="value" style={{ color: "#475569" }}>
                    {detailsModal.updated_at ? new Date(detailsModal.updated_at).toLocaleDateString() : "—"}
                  </span>
                </div>
                <div className="prj-overview-card full">
                  <span className="label">Description & Scope</span>
                  <span className="value" style={{ fontWeight: 400, color: "#334155", lineHeight: 1.5 }}>
                    {detailsModal.description || "No project description provided."}
                  </span>
                </div>
              </div>

              {/* ========================================================
                  FEATURE 3: PROJECT ROLES & TEAM ASSIGNMENTS
                  ======================================================== */}
              <div className="prj-roles-team-section">
                <div className="prj-roles-team-header">
                  <div className="prj-roles-team-title">
                    <ShieldCheck size={18} color="#047857" />
                    <h4>PROJECT ROLES & TEAM</h4>
                  </div>
                  <div className="prj-roles-team-header-actions">
                    <span className="prj-roles-count-badge">
                      {detailsRoles.length} {detailsRoles.length === 1 ? "Role" : "Roles"}
                    </span>
                    <button
                      type="button"
                      className="prj-roles-refresh-btn"
                      onClick={() => loadDetailsRoles(detailsModal.id)}
                      title="Refresh Project Roles & Team"
                      aria-label="Refresh Project Roles & Team"
                    >
                      <RefreshCw size={13} className={loadingDetailsRoles ? "spinner" : ""} />
                      <span>Refresh</span>
                    </button>
                  </div>
                </div>

                {loadingDetailsRoles ? (
                  <div className="prj-roles-loading">
                    <Loader2 size={24} className="spinner text-emerald" />
                    <span>Loading project roles and assigned team...</span>
                  </div>
                ) : detailsRoles.length === 0 ? (
                  <div className="prj-roles-empty">
                    <Users size={32} color="#94a3b8" />
                    <p>No project roles have been created yet.</p>
                  </div>
                ) : (
                  <div className="prj-roles-cards-grid">
                    {detailsRoles.map((role) => {
                      const assignedCount = role.assigned_employees ? role.assigned_employees.length : (role.assigned_headcount || 0);
                      const requiredCount = role.required_headcount || 1;
                      const isFilled = assignedCount >= requiredCount;

                      return (
                        <div key={role.id} className="prj-role-detail-card">
                          <div className="prj-role-detail-header">
                            <div className="prj-role-title-wrap">
                              <h5 className="prj-role-detail-name">{role.role_name}</h5>
                              {role.description && (
                                <p className="prj-role-detail-desc">{role.description}</p>
                              )}
                            </div>
                            <span className={`prj-role-status-badge ${isFilled ? "filled" : "open"}`}>
                              {isFilled ? "Filled" : "Open Positions"}
                            </span>
                          </div>

                          <div className="prj-role-metrics-row">
                            <div className="prj-role-metric">
                              <span className="metric-lbl">Required Headcount:</span>
                              <span className="metric-val">{requiredCount}</span>
                            </div>
                            <div className="prj-role-metric">
                              <span className="metric-lbl">Assigned:</span>
                              <span className="metric-val">
                                <strong>{assignedCount}</strong> / {requiredCount}
                              </span>
                            </div>
                          </div>

                          {/* Assigned Employees */}
                          <div className="prj-role-assigned-section">
                            <div className="prj-role-assigned-title">
                              <Users size={14} color="#047857" />
                              <span>Assigned Employees</span>
                            </div>

                            {(!role.assigned_employees || role.assigned_employees.length === 0) ? (
                              <div className="prj-role-no-employees">
                                No employees assigned to this role yet.
                              </div>
                            ) : (
                              <div className="prj-role-employees-list">
                                {role.assigned_employees.map((emp) => {
                                  const empName = emp.employee_name || emp.full_name || [emp.first_name, emp.last_name].filter(Boolean).join(" ") || "Employee";
                                  const empCode = emp.employee_code || (emp.employee_id ? `EMP${String(emp.employee_id).padStart(3, "0")}` : "—");
                                  const empDesignation = emp.designation || emp.official_designation || emp.department || "Team Member";

                                  return (
                                    <div key={emp.assignment_id || emp.employee_id} className="prj-assigned-emp-pill">
                                      <div className="emp-avatar-sm">
                                        {empName.charAt(0).toUpperCase()}
                                      </div>
                                      <div className="emp-info-wrap">
                                        <div className="emp-name-row">
                                          <span className="emp-name">{empName}</span>
                                          <span className="emp-code-pill">{empCode}</span>
                                        </div>
                                        <span className="emp-designation">{empDesignation}</span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="prj-modal-footer">
              <button className="prj-primary-btn" onClick={() => setDetailsModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 2: EDIT PROJECT MODAL
          Contains ONLY 3 required sections:
          - Section 1: Project Information
          - Section 2: Project Details & Schedule
          - Section 5: Project Status & Management
          (Sections 3 & 4 removed per enterprise architecture)
          ======================================================== */}
      {editModal && (
        <div className="prj-modal-overlay" onClick={() => setEditModal(null)}>
          <div className="prj-modal-card large" onClick={(e) => e.stopPropagation()}>
            <div className="prj-modal-header">
              <div>
                <h3>Edit Project Management Desk</h3>
                <p>{editForm.project_code} • {editForm.project_name}</p>
              </div>
              <button className="prj-modal-close" onClick={() => setEditModal(null)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveEditProject}>
              <div className="prj-modal-body">
                {editError && (
                  <div
                    style={{
                      marginBottom: "16px",
                      padding: "12px 16px",
                      borderRadius: "8px",
                      background: "#fef2f2",
                      color: "#991b1b",
                      border: "1px solid #fecaca",
                      fontSize: "13px",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{editError}</span>
                  </div>
                )}

                {loadingEditData ? (
                  <div style={{ textAlign: "center", padding: "40px 0" }}>
                    <Loader2 size={32} className="spinner text-emerald" style={{ margin: "0 auto 8px auto" }} />
                    <p style={{ color: "#64748b" }}>Loading project details...</p>
                  </div>
                ) : (
                  <>
                    {/* SECTION 1: PROJECT INFORMATION */}
                    <section className="prj-edit-section-card">
                      <div className="prj-section-title-bar">
                        <div>
                          <h4><Settings size={18} color="#047857" /> Section 1: Project Information</h4>
                          <p>Core governance, stakeholder attributes, and scope definition</p>
                        </div>
                      </div>

                      <div className="prj-form-grid">
                        <div className="prj-form-group">
                          <label>Project Code (Read-Only)</label>
                          <input
                            type="text"
                            value={editForm.project_code}
                            disabled
                            className="prj-form-input"
                            style={{ background: "#f8fafc", color: "#64748b", cursor: "not-allowed" }}
                          />
                        </div>

                        <div className="prj-form-group">
                          <label>Project Name *</label>
                          <input
                            type="text"
                            value={editForm.project_name}
                            onChange={(e) => setEditForm({ ...editForm, project_name: e.target.value })}
                            required
                            className="prj-form-input"
                          />
                        </div>

                        <div className="prj-form-group">
                          <label>Client / Stakeholder Name</label>
                          <input
                            type="text"
                            value={editForm.client_name}
                            onChange={(e) => setEditForm({ ...editForm, client_name: e.target.value })}
                            placeholder="e.g. Mediatize"
                            className="prj-form-input"
                          />
                        </div>

                        <div className="prj-form-group">
                          <label>Priority</label>
                          <select
                            value={editForm.priority}
                            onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                            className="prj-form-select"
                          >
                            <option value="LOW">LOW</option>
                            <option value="MEDIUM">MEDIUM</option>
                            <option value="HIGH">HIGH</option>
                            <option value="CRITICAL">CRITICAL</option>
                          </select>
                        </div>

                        <div className="prj-form-group full">
                          <label>Description & Scope</label>
                          <textarea
                            rows={3}
                            value={editForm.description}
                            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                            className="prj-form-textarea"
                            placeholder="Describe deliverables, sprint milestones, and engineering expectations..."
                          />
                        </div>
                      </div>
                    </section>

                    {/* SECTION 2: PROJECT DETAILS / CONFIGURATION */}
                    <section className="prj-edit-section-card">
                      <div className="prj-section-title-bar">
                        <div>
                          <h4><Calendar size={18} color="#047857" /> Section 2: Project Details & Schedule</h4>
                          <p>Timeline scheduling and target delivery window</p>
                        </div>
                      </div>

                      <div className="prj-form-grid">
                        <div className="prj-form-group">
                          <label>Start Date *</label>
                          <input
                            type="date"
                            value={editForm.start_date}
                            onChange={(e) => setEditForm({ ...editForm, start_date: e.target.value })}
                            required
                            className="prj-form-input"
                          />
                        </div>

                        <div className="prj-form-group">
                          <label>Expected End Date *</label>
                          <input
                            type="date"
                            value={editForm.expected_end_date}
                            onChange={(e) => setEditForm({ ...editForm, expected_end_date: e.target.value })}
                            required
                            className="prj-form-input"
                          />
                        </div>
                      </div>
                    </section>

                    {/* SECTION 3: PROJECT STATUS / MANAGEMENT */}
                    <section className="prj-edit-section-card">
                      <div className="prj-section-title-bar">
                        <div>
                          <h4><Sliders size={18} color="#047857" /> Section 3: Project Status & Management</h4>
                          <p>Track delivery lifecycle status and completion percentage (0 - 100%)</p>
                        </div>
                      </div>

                      <div className="prj-form-grid">
                        <div className="prj-form-group">
                          <label>Project Status</label>
                          <select
                            value={editForm.status}
                            onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                            className="prj-form-select"
                          >
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="PLANNING">PLANNING</option>
                            <option value="UPCOMING">UPCOMING</option>
                            <option value="ON_HOLD">ON_HOLD</option>
                            <option value="COMPLETED">COMPLETED</option>
                            <option value="CANCELLED">CANCELLED</option>
                          </select>
                        </div>

                        <div className="prj-form-group">
                          <label>Completion Percentage: {editForm.progress_percentage}%</label>
                          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "6px" }}>
                            <input
                              type="range"
                              min="0"
                              max="100"
                              value={editForm.progress_percentage}
                              onChange={(e) => {
                                const val = parseInt(e.target.value, 10);
                                setEditForm({
                                  ...editForm,
                                  progress_percentage: val,
                                  status: val === 100 ? "COMPLETED" : editForm.status,
                                });
                              }}
                              style={{ flex: 1, accentColor: "#047857", cursor: "pointer" }}
                            />
                            <input
                              type="number"
                              min="0"
                              max="100"
                              value={editForm.progress_percentage}
                              onChange={(e) => {
                                const val = Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                setEditForm({
                                  ...editForm,
                                  progress_percentage: val,
                                  status: val === 100 ? "COMPLETED" : editForm.status,
                                });
                              }}
                              style={{
                                width: "64px",
                                padding: "6px 8px",
                                borderRadius: "6px",
                                border: "1px solid #cbd5e1",
                                textAlign: "center",
                                fontWeight: 700,
                              }}
                            />
                            <span style={{ fontSize: "14px", fontWeight: 700, color: "#64748b" }}>%</span>
                          </div>
                        </div>

                        {/* Visual Progress Track */}
                        <div className="prj-form-group full">
                          <div className="prj-progress-wrap">
                            <div className="prj-progress-header">
                              <span>Progress Track</span>
                              <span className="prj-progress-val">{editForm.progress_percentage}%</span>
                            </div>
                            <div className="prj-progress-track">
                              <div
                                className={`prj-progress-fill ${editForm.progress_percentage === 100 ? "completed" : ""}`}
                                style={{ width: `${editForm.progress_percentage}%` }}
                              />
                            </div>
                          </div>
                          <small style={{ color: "#64748b", marginTop: "6px", display: "block", fontSize: "11.5px" }}>
                            Note: Setting completion to 100% automatically sets the status to COMPLETED upon save.
                          </small>
                        </div>
                      </div>
                    </section>
                  </>
                )}
              </div>

              <div className="prj-modal-footer">
                <button type="button" className="prj-btn-ghost" onClick={() => setEditModal(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="prj-primary-btn"
                  disabled={savingEdit || loadingEditData || !editForm.project_name.trim() || !editForm.start_date}
                >
                  {savingEdit ? "Saving Changes..." : "Save Project Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 3: CREATE PROJECT MODAL
          ======================================================== */}
      {createModal && (
        <div className="prj-modal-overlay" onClick={() => setCreateModal(false)}>
          <div className="prj-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="prj-modal-header">
              <div>
                <h3>Create New Project</h3>
                <p>Register a new delivery initiative within Mediatize HRMS</p>
              </div>
              <button className="prj-modal-close" onClick={() => setCreateModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateProject}>
              <div className="prj-modal-body">
                {createError && (
                  <div
                    style={{
                      marginBottom: "16px",
                      padding: "12px 16px",
                      borderRadius: "8px",
                      background: "#fef2f2",
                      color: "#991b1b",
                      border: "1px solid #fecaca",
                      fontSize: "13px",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <AlertCircle size={16} />
                    <span>{createError}</span>
                  </div>
                )}

                {/* Section: Project Information */}
                <div style={{ marginBottom: "16px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>
                    Project Information
                  </h4>
                  <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                    Primary identifier, governance name, and baseline status
                  </p>
                </div>

                <div className="prj-form-grid">
                  <div className="prj-form-group">
                    <label>Project Code</label>
                    <input
                      type="text"
                      placeholder="e.g. PRJ001 (auto-generated if empty)"
                      value={createForm.project_code}
                      onChange={(e) => setCreateForm({ ...createForm, project_code: e.target.value.toUpperCase() })}
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group">
                    <label>Project Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Mediatize Cloud Portal"
                      value={createForm.project_name}
                      onChange={(e) => setCreateForm({ ...createForm, project_name: e.target.value })}
                      required
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group">
                    <label>Status</label>
                    <select
                      value={createForm.status}
                      onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}
                      className="prj-form-select"
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="PLANNING">PLANNING</option>
                      <option value="UPCOMING">UPCOMING</option>
                      <option value="ON_HOLD">ON_HOLD</option>
                    </select>
                  </div>

                  <div className="prj-form-group">
                    <label>Priority</label>
                    <select
                      value={createForm.priority}
                      onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                      className="prj-form-select"
                    >
                      <option value="LOW">LOW</option>
                      <option value="MEDIUM">MEDIUM</option>
                      <option value="HIGH">HIGH</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </div>
                </div>

                {/* Section: Project Details */}
                <div style={{ margin: "20px 0 16px 0", borderTop: "1px solid #e2e8f0", paddingTop: "16px" }}>
                  <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>
                    Project Details
                  </h4>
                  <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                    Client stakeholder, scheduling boundaries, and deliverables scope
                  </p>
                </div>

                <div className="prj-form-grid">
                  <div className="prj-form-group full">
                    <label>Client Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Mediatize Internal"
                      value={createForm.client_name}
                      onChange={(e) => setCreateForm({ ...createForm, client_name: e.target.value })}
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group">
                    <label>Start Date *</label>
                    <input
                      type="date"
                      value={createForm.start_date}
                      onChange={(e) => setCreateForm({ ...createForm, start_date: e.target.value })}
                      required
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group">
                    <label>Expected End Date</label>
                    <input
                      type="date"
                      value={createForm.expected_end_date}
                      onChange={(e) => setCreateForm({ ...createForm, expected_end_date: e.target.value })}
                      className="prj-form-input"
                    />
                  </div>

                  <div className="prj-form-group full">
                    <label>Description</label>
                    <textarea
                      rows={3}
                      placeholder="Outline sprint scope, deliverables, and technical criteria..."
                      value={createForm.description}
                      onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                      className="prj-form-textarea"
                    />
                  </div>
                </div>
              </div>

              <div className="prj-modal-footer">
                <button type="button" className="prj-btn-ghost" onClick={() => setCreateModal(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="prj-primary-btn"
                  disabled={
                    submittingCreate ||
                    !createForm.project_name.trim() ||
                    !createForm.start_date
                  }
                >
                  {submittingCreate ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
