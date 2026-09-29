import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { 
  FolderKanban, 
  ArrowLeft, 
  CheckCircle2, 
  Calendar, 
  Users, 
  ShieldCheck, 
  Search, 
  Briefcase, 
  X, 
  Loader2,
  ExternalLink,
  ShieldAlert,
  TrendingUp,
  AlertTriangle,
  Clock
} from "lucide-react";
import { projectService } from "../services/api";
import "../styles/Projects.css";

export default function EmployeeProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProject, setSelectedProject] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const loadAssigned = async () => {
    setLoading(true);
    try {
      const data = await projectService.getMyProjects();
      setProjects(data || []);
    } catch (err) {
      console.error("Failed to load assigned projects:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssigned();
  }, []);

  const handleOpenDetails = async (projectId) => {
    setDetailsLoading(true);
    try {
      let proj;
      try {
        proj = await projectService.getMyProjectDetails(projectId);
      } catch (e) {
        proj = await projectService.getProject(projectId);
      }
      setSelectedProject(proj);
    } catch (err) {
      console.error("Could not fetch project details:", err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const filteredProjects = projects.filter((p) => {
    const matchesFilter =
      activeFilter === "ALL" ||
      (activeFilter === "ACTIVE" && p.status === "ACTIVE") ||
      (activeFilter === "COMPLETED" && p.status === "COMPLETED") ||
      (activeFilter === "ON_HOLD" && p.status === "ON_HOLD");

    const matchesSearch =
      !searchQuery ||
      p.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.project_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.my_role && p.my_role.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesFilter && matchesSearch;
  });

  const activeCount = projects.filter((p) => p.status === "ACTIVE").length;
  const completedCount = projects.filter((p) => p.status === "COMPLETED").length;
  const onHoldCount = projects.filter((p) => p.status === "ON_HOLD").length;

  return (
    <div className="prj-page-wrapper">
      {/* ================= HEADER BAR ================= */}
      <header className="prj-header-bar">
        <div className="prj-header-container">
          <div className="prj-header-left">
            <Link to="/employee/dashboard" className="prj-back-btn">
              <ArrowLeft size={16} />
              <span>Staff Dashboard</span>
            </Link>
            <div className="prj-header-meta">
              <h2>My Assigned Projects</h2>
              <span>Mediatize Staff Portal • Active Sprint Initiatives & Collaborative Rosters</span>
            </div>
          </div>
          <div className="dir-tag-viewonly">
            <span>Read-Only Assignment Desk</span>
          </div>
        </div>
      </header>

      {/* ================= MAIN CONTENT ================= */}
      <main className="prj-content-container">
        {/* Notice of Governance */}
        <div
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            padding: "14px 18px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "20px",
          }}
        >
          <ShieldAlert size={20} color="#047857" style={{ flexShrink: 0 }} />
          <p style={{ margin: 0, fontSize: "13px", color: "#475569", lineHeight: 1.4 }}>
            You are viewing project initiatives currently assigned to your employee account. Project allocations, sprint roles, and milestone statuses are managed by HR administration.
          </p>
        </div>

        {/* METRICS OVERVIEW */}
        <section className="prj-metric-strip">
          <div className="prj-metric-card">
            <div className="prj-metric-header">
              <span>MY PROJECTS</span>
              <FolderKanban size={18} color="#047857" />
            </div>
            <div className="prj-metric-value">{projects.length}</div>
            <span className="prj-metric-sub">Initiatives assigned to you</span>
          </div>

          <div className="prj-metric-card">
            <div className="prj-metric-header">
              <span>ACTIVE SPRINTS</span>
              <CheckCircle2 size={18} color="#059669" />
            </div>
            <div className="prj-metric-value" style={{ color: "#047857" }}>
              {activeCount}
            </div>
            <span className="prj-metric-sub">Currently in development</span>
          </div>

          <div className="prj-metric-card">
            <div className="prj-metric-header">
              <span>COMPLETED ARCHIVE</span>
              <Briefcase size={18} color="#64748b" />
            </div>
            <div className="prj-metric-value">{completedCount}</div>
            <span className="prj-metric-sub">Delivered deliverables</span>
          </div>
        </section>

        {/* TOOLBAR & FILTERS */}
        <section className="prj-toolbar-card">
          <div className="prj-filter-pills">
            <button
              className={`prj-filter-btn ${activeFilter === "ALL" ? "active" : ""}`}
              onClick={() => setActiveFilter("ALL")}
            >
              All Projects <span className="counter">{projects.length}</span>
            </button>
            <button
              className={`prj-filter-btn ${activeFilter === "ACTIVE" ? "active" : ""}`}
              onClick={() => setActiveFilter("ACTIVE")}
            >
              Active <span className="counter">{activeCount}</span>
            </button>
            <button
              className={`prj-filter-btn ${activeFilter === "COMPLETED" ? "active" : ""}`}
              onClick={() => setActiveFilter("COMPLETED")}
            >
              Completed <span className="counter">{completedCount}</span>
            </button>
            {onHoldCount > 0 && (
              <button
                className={`prj-filter-btn ${activeFilter === "ON_HOLD" ? "active" : ""}`}
                onClick={() => setActiveFilter("ON_HOLD")}
              >
                On Hold <span className="counter">{onHoldCount}</span>
              </button>
            )}
          </div>

          <div className="prj-search-box">
            <Search size={16} className="prj-search-icon" />
            <input
              type="text"
              placeholder="Search assigned projects or roles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="prj-search-input"
            />
          </div>
        </section>

        {/* PROJECT CARDS */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <Loader2 size={36} className="spinner text-emerald" style={{ margin: "0 auto 12px auto" }} />
            <p style={{ color: "#64748b", fontSize: "14px", fontWeight: "500" }}>Loading assigned projects...</p>
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
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
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

                    <p className="prj-card-desc">{p.description || "Active corporate sprint initiative."}</p>

                    <div className="prj-card-meta-list">
                      <div className="prj-card-meta-item">
                        <span>My Assigned Role:</span>
                        <span className="prj-role-highlight">
                          <ShieldCheck size={13} />
                          {p.my_role || "Role not assigned"}
                        </span>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Team Size:</span>
                        <strong>{p.team_members_count || 1} Members</strong>
                      </div>
                      <div className="prj-card-meta-item">
                        <span>Timeline:</span>
                        <strong>
                          {p.start_date} → {p.expected_end_date}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="prj-card-actions">
                    <button
                      className="prj-btn-primary-sm"
                      onClick={() => handleOpenDetails(p.id)}
                      style={{ width: "100%", justifyContent: "center" }}
                    >
                      <ExternalLink size={14} />
                      <span>View Project Details & Team</span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="prj-empty-box" style={{ background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
            <FolderKanban size={48} color="#047857" style={{ margin: "0 auto 12px auto" }} />
            <h4>No Projects Assigned</h4>
            <p>
              {searchQuery
                ? `No assigned projects match "${searchQuery}".`
                : "You are not currently assigned to any active enterprise projects. When HR allocates you to an initiative, it will appear here."}
            </p>
          </div>
        )}
      </main>

      {/* ================= EMPLOYEE PROJECT DETAILS MODAL ================= */}
      {selectedProject && (
        <div className="prj-modal-overlay" onClick={() => setSelectedProject(null)}>
          <div className="prj-modal-card large" onClick={(e) => e.stopPropagation()}>
            <div className="prj-modal-header">
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                  <span className="prj-code-badge">{selectedProject.project_code}</span>
                  {selectedProject.priority && (
                    <span className={`prj-priority-pill ${selectedProject.priority.toLowerCase()}`}>
                      {selectedProject.priority}
                    </span>
                  )}
                  <span className={`prj-status-pill ${selectedProject.status.toLowerCase()}`}>
                    <span className="dot" />
                    {selectedProject.status}
                  </span>
                </div>
                <h3>{selectedProject.project_name}</h3>
                <p>{selectedProject.description || "Project Overview & Sprint Specifications"}</p>
              </div>
              <button className="prj-modal-close" onClick={() => setSelectedProject(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="prj-modal-body">
              {/* Highlight of My Role */}
              <div
                style={{
                  background: "#ecfdf5",
                  border: "1px solid #a7f3d0",
                  borderRadius: "12px",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "20px",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#065f46", textTransform: "uppercase" }}>
                    YOUR ALLOCATED ROLE
                  </span>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#047857", marginTop: "2px" }}>
                    {selectedProject.my_role || "Role not assigned"}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#065f46", textTransform: "uppercase" }}>
                    TIMELINE
                  </span>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a", marginTop: "2px" }}>
                    {selectedProject.start_date} → {selectedProject.expected_end_date}
                  </div>
                </div>
              </div>

              {/* Progress Bar Preview */}
              <div
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  padding: "14px 18px",
                  marginBottom: "20px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#0f172a", display: "flex", alignItems: "center", gap: "6px" }}>
                    <TrendingUp size={14} color="#047857" /> Sprint Completion
                  </span>
                  <span style={{ fontSize: "14px", fontWeight: 800, color: "#047857" }}>
                    {selectedProject.progress_percentage || 0}%
                  </span>
                </div>
                <div className="prj-progress-track">
                  <div
                    className={`prj-progress-fill ${selectedProject.progress_percentage === 100 ? "completed" : ""}`}
                    style={{ width: `${Math.min(100, Math.max(0, selectedProject.progress_percentage || 0))}%` }}
                  />
                </div>
              </div>

              {/* Team Members List */}
              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", color: "#0f172a" }}>
                    Project Team Members ({selectedProject.members?.length || 0})
                  </h4>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>Read-Only Collaboration Directory</span>
                </div>

                {selectedProject.members && selectedProject.members.length > 0 ? (
                  <div className="prj-member-list">
                    {selectedProject.members.map((m) => (
                      <div key={m.id || m.employee_id} className="prj-member-row">
                        <div className="prj-member-info">
                          <div className="prj-avatar-circle">
                            {m.profile_photo_url ? (
                              <img src={m.profile_photo_url} alt={m.full_name} className="prj-avatar-img" />
                            ) : (
                              (m.full_name || m.first_name || "E")[0]
                            )}
                          </div>
                          <div className="prj-member-names">
                            <strong>{m.full_name || `${m.first_name} ${m.last_name}`}</strong>
                            <span>{m.employee_code}</span>
                          </div>
                        </div>

                        <div className="prj-member-meta">
                          <span className="prj-role-highlight">
                            <ShieldCheck size={13} />
                            {m.project_role_name || "Member"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="prj-empty-box" style={{ background: "#f8fafc", borderRadius: "12px" }}>
                    <Users size={32} color="#94a3b8" style={{ margin: "0 auto 8px auto" }} />
                    <p>No other team members currently assigned.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="prj-modal-footer">
              <button className="prj-btn-ghost" onClick={() => setSelectedProject(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
