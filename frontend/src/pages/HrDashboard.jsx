import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { 
  Users, 
  FolderKanban, 
  ShieldCheck, 
  CalendarCheck, 
  CalendarDays, 
  TriangleAlert, 
  FileChartColumn, 
  Megaphone, 
  Bell, 
  History, 
  LogOut, 
  Menu, 
  X, 
  Plus, 
  ArrowRight, 
  UserCheck, 
  UserX, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Briefcase,
  Layers,
  User,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Inbox
} from "lucide-react";
import { authService, dashboardService } from "../services/api";
import { broadcastChannel } from "../services/authSync";
import ProfileDropdown from "../components/ProfileDropdown";
import CreateEmployeeModal from "../components/CreateEmployeeModal";
import "../styles/HrDashboard.css";
import "../styles/HrEmployees.css";

export default function HrDashboard({ onToggleSidebar }) {
  const navigate = useNavigate();
  const location = useLocation();

  const hrNavigationItems = [
    { label: "Dashboard", path: "/hr/dashboard", icon: Users, enabled: true },
    { label: "My Profile", path: "/hr/profile", icon: User, enabled: true },
    { label: "Employees", path: "/hr/employees", icon: Users, enabled: true },
    { label: "Projects", path: "/hr/projects", icon: FolderKanban, enabled: true },
    { label: "Project Roles", path: "/hr/project-roles", icon: ShieldCheck, enabled: true },
    { label: "Announcements", path: "/hr/announcements", icon: Megaphone, enabled: true },
    { label: "Work Reports", path: "/hr/work-reports", icon: FileChartColumn, enabled: true },
    { label: "Complaints", path: "/hr/complaints", icon: TriangleAlert, enabled: true },
    { label: "Attendance", path: "/hr/attendance", icon: CalendarCheck, enabled: true },
    { label: "Leave Management", path: "/hr/leave", icon: CalendarDays, enabled: true },
    { label: "Audit Logs", path: "/hr/audit-logs", icon: History, enabled: true },
    { label: "Notifications", path: "/hr/notifications", icon: Bell, enabled: true },
  ];

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          name: parsed.full_name || (parsed.first_name ? `${parsed.first_name} ${parsed.last_name || ""}`.trim() : parsed.email?.split("@")[0] || "HR Administrator"),
          email: parsed.email || "",
          role: (parsed.role || "HR").toUpperCase(),
          photo: parsed.profile_photo_url || null,
        };
      }
    } catch {}
    return {
      name: "HR Administrator",
      email: "",
      role: "HR",
      photo: null,
    };
  });

  const [summary, setSummary] = useState({
    total_employees: 0,
    active_employees: 0,
    inactive_employees: 0,
    on_leave_today: 0,
    active_projects: 0,
    total_projects: 0,
    pending_leave_requests: 0,
    open_complaints: 0,
    pending_work_reports: 0,
    unread_notifications: 0,
    active_projects_list: [],
    recent_employees: [],
  });

  const [unreadCount, setUnreadCount] = useState(() => {
    const cached = localStorage.getItem("hrms_unread_notifs");
    return cached !== null ? parseInt(cached, 10) : 0;
  });

  const [currentTime, setCurrentTime] = useState("");
  const [currentDate, setCurrentDate] = useState("");
  const [greeting, setGreeting] = useState("Good Afternoon");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createEmployeeModalOpen, setCreateEmployeeModalOpen] = useState(false);
  const [dashboardToast, setDashboardToast] = useState({ type: "", message: "" });

  const fetchDashboardData = async () => {
    setLoading(true);
    setError("");

    try {
      const [meData, sumData] = await Promise.all([
        authService.getMe().catch(() => null),
        dashboardService.getHrDashboardSummary(),
      ]);

      if (meData) {
        setCurrentUser({
          name: meData.full_name || (meData.first_name ? `${meData.first_name} ${meData.last_name || ""}`.trim() : meData.email.split("@")[0]),
          email: meData.email,
          role: (meData.role || "HR").toUpperCase(),
          photo: meData.profile_photo_url || null,
        });
      }

      if (sumData) {
        setSummary(sumData);
        if (sumData.unread_notifications !== undefined) {
          setUnreadCount(sumData.unread_notifications);
          localStorage.setItem("hrms_unread_notifs", String(sumData.unread_notifications));
        }
      }
    } catch (err) {
      console.error("HR Dashboard fetch error:", err);
      setError("Unable to load real-time workforce metrics from server.");
    } finally {
      setLoading(false);
    }
  };

  const handleDashboardEmployeeCreated = (created, payload) => {
    setDashboardToast({
      type: "success",
      message: `Employee account created for ${created.first_name} ${created.last_name} (${created.employee_code}) with designation "${created.designation || payload.designation}". An onboarding welcome email was sent to ${payload.email}!`,
    });
    fetchDashboardData();
  };

  // Live Clock & Greeting
  useEffect(() => {
    const updateDateTime = () => {
      const now = new Date();
      const hours = now.getHours();
      if (hours < 12) setGreeting("Good Morning");
      else if (hours < 17) setGreeting("Good Afternoon");
      else setGreeting("Good Evening");

      setCurrentTime(now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      setCurrentDate(now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" }));
    };

    updateDateTime();
    const clockTimer = setInterval(updateDateTime, 1000);
    return () => clearInterval(clockTimer);
  }, []);

  // Sync unread notification count across tabs and local events
  useEffect(() => {
    const handleNotifUpdate = (e) => {
      if (e?.detail) {
        if (e.detail.count !== undefined) {
          setUnreadCount(Math.max(0, e.detail.count));
        } else if (e.detail.delta !== undefined) {
          setUnreadCount((prev) => Math.max(0, prev + e.detail.delta));
        }
      }
    };

    const handleStorage = (e) => {
      if (e.key === "hrms_unread_notifs" && e.newValue !== null) {
        const val = parseInt(e.newValue, 10);
        if (!isNaN(val)) setUnreadCount(val);
      }
    };

    const handleBroadcast = (event) => {
      const data = event.data || {};
      if (data.type === "NOTIF_COUNT_UPDATE") {
        if (data.unreadCount !== undefined) {
          setUnreadCount(Math.max(0, data.unreadCount));
        } else if (data.delta !== undefined) {
          setUnreadCount((prev) => Math.max(0, prev + data.delta));
        }
      }
    };

    window.addEventListener("unreadNotificationsUpdated", handleNotifUpdate);
    window.addEventListener("storage", handleStorage);
    if (broadcastChannel) {
      broadcastChannel.addEventListener("message", handleBroadcast);
    }

    return () => {
      window.removeEventListener("unreadNotificationsUpdated", handleNotifUpdate);
      window.removeEventListener("storage", handleStorage);
      if (broadcastChannel) {
        broadcastChannel.removeEventListener("message", handleBroadcast);
      }
    };
  }, []);

  // Fetch Live Backend Data from /api/hr/dashboard/summary and /api/auth/me
  useEffect(() => {
    fetchDashboardData();

    const handleProfileSync = (e) => {
      if (e?.detail) {
        setCurrentUser((prev) => ({
          ...prev,
          name: e.detail.full_name || (e.detail.first_name ? `${e.detail.first_name} ${e.detail.last_name || ""}`.trim() : prev.name),
          photo: e.detail.profile_photo_url || prev.photo,
        }));
      }
    };
    window.addEventListener("profileUpdated", handleProfileSync);
    return () => window.removeEventListener("profileUpdated", handleProfileSync);
  }, []);

  const handleSignOut = () => {
    authService.logout();
  };

  return (
    <div className="hr-enterprise-layout">
      {/* ================= MAIN CONTENT WRAPPER ================= */}
      <div className="hr-main-content-wrapper">
        
        {/* Top Header */}
        <header className="enterprise-top-header">
          <div className="header-left-group">
            {onToggleSidebar && (
              <button className="mobile-menu-toggle" onClick={onToggleSidebar} aria-label="Open menu">
                <Menu size={20} />
              </button>
            )}
            <div className="header-breadcrumb">
              <span>Portal</span>
              <span className="sep">/</span>
              <span className="current">Workforce Dashboard</span>
            </div>
          </div>

          <div className="nav-user-controls">
            <div className="header-clock-box">
              <span>{currentDate}</span>
              <strong>{currentTime}</strong>
            </div>

            <button
              className="header-icon-btn"
              title={unreadCount > 0 ? "You have unread notifications" : "No Unread Notifications"}
              onClick={() => navigate("/hr/notifications")}
              id="btn-hr-notifications"
              aria-label="System Notifications"
            >
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="notif-dot" id="hr-notif-dot" aria-hidden="true" />
              )}
            </button>

            <button
              type="button"
              className="dir-primary-create-btn"
              onClick={() => setCreateEmployeeModalOpen(true)}
              id="btn-open-create-employee"
              title="Create New Employee"
              style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <Plus size={16} />
              <span>Create Employee</span>
            </button>

            <ProfileDropdown currentUser={currentUser} role="hr" />
          </div>
        </header>

        {/* Workspace Body */}
        <main className="hr-command-workspace">
          
          {/* Welcome Banner */}
          <div className="command-hero-banner">
            <div>
              <h1>{greeting}, {currentUser.name}</h1>
              <p>Here's your real-time workforce overview and enterprise command deck for today.</p>
            </div>
            <div className="hero-quick-actions">
              <button
                type="button"
                className="hero-cta-btn primary"
                onClick={() => setCreateEmployeeModalOpen(true)}
                id="btn-hero-create-employee"
                style={{ cursor: "pointer", border: "none" }}
              >
                <Plus size={16} /> Create Employee
              </button>
              <Link to="/hr/projects" className="hero-cta-btn secondary">
                <FolderKanban size={16} /> View Projects
              </Link>
            </div>
          </div>

          {dashboardToast.message && (
            <div 
              className={`dir-alert-banner ${dashboardToast.type}`} 
              style={{ marginBottom: "20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {dashboardToast.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                <span>{dashboardToast.message}</span>
              </div>
              <button 
                type="button" 
                className="modal-close-btn" 
                onClick={() => setDashboardToast({ type: "", message: "" })}
                aria-label="Dismiss message"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {error && (
            <div className="hr-error-banner">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {/* ================= SUMMARY CARDS (LIVE BACKEND DATA) ================= */}
          <div className="hr-kpi-grid">
            <div className="kpi-card-ent emerald">
              <div className="kpi-top-row">
                <span>TOTAL EMPLOYEES</span>
                <Users size={18} className="ico-emerald" />
              </div>
              <h2>{loading ? "..." : summary.total_employees}</h2>
              <small className="kpi-sub positive">
                <UserCheck size={12} /> {summary.active_employees} Active personnel
              </small>
            </div>

            <div className="kpi-card-ent blue">
              <div className="kpi-top-row">
                <span>ACTIVE EMPLOYEES</span>
                <UserCheck size={18} className="ico-blue" />
              </div>
              <h2>{loading ? "..." : summary.active_employees}</h2>
              <small className="kpi-sub">
                {summary.inactive_employees} Inactive / On Notice
              </small>
            </div>

            <div className="kpi-card-ent amber">
              <div className="kpi-top-row">
                <span>ON LEAVE TODAY</span>
                <CalendarDays size={18} className="ico-amber" />
              </div>
              <h2>{loading ? "..." : summary.on_leave_today}</h2>
              <small className="kpi-sub">Approved absences</small>
            </div>

            <div className="kpi-card-ent purple">
              <div className="kpi-top-row">
                <span>ACTIVE PROJECTS</span>
                <FolderKanban size={18} className="ico-purple" />
              </div>
              <h2>{loading ? "..." : summary.active_projects}</h2>
              <small className="kpi-sub positive">
                {summary.completed_projects || 0} Completed • {summary.total_projects || 0} Total
              </small>
            </div>

            <div className="kpi-card-ent blue">
              <div className="kpi-top-row">
                <span>PROJECT MEMBERS</span>
                <Users size={18} className="ico-blue" />
              </div>
              <h2>{loading ? "..." : summary.project_members || 0}</h2>
              <small className="kpi-sub positive">
                Assigned workforce personnel
              </small>
            </div>

            <div className="kpi-card-ent rose">
              <div className="kpi-top-row">
                <span>PENDING LEAVES</span>
                <Clock size={18} className="ico-rose" />
              </div>
              <h2>{loading ? "..." : summary.pending_leave_requests}</h2>
              <small className="kpi-sub">Awaiting HR review</small>
            </div>

            <div className="kpi-card-ent teal">
              <div className="kpi-top-row">
                <span>OPEN COMPLAINTS</span>
                <TriangleAlert size={18} className="ico-teal" />
              </div>
              <h2>{loading ? "..." : summary.open_complaints}</h2>
              <small className="kpi-sub">Grievances filed</small>
            </div>

            <div className="kpi-card-ent indigo">
              <div className="kpi-top-row">
                <span>WORK REPORTS</span>
                <FileChartColumn size={18} className="ico-indigo" />
              </div>
              <h2>{loading ? "..." : summary.pending_work_reports}</h2>
              <small className="kpi-sub">Daily sprint reports</small>
            </div>
          </div>

          {/* ================= ACTION CENTER & EMPLOYEE BREAKDOWN ================= */}
          <div className="hr-dual-grid">
            
            {/* HR Action Center */}
            <div className="enterprise-panel">
              <div className="panel-header-row">
                <div className="panel-title-wrap">
                  <Inbox size={18} className="text-emerald" />
                  <h3>HR Action Center</h3>
                </div>
                <span className="badge-pill">Operational Queue</span>
              </div>

              <div className="action-items-stack">
                <div className="action-row">
                  <div className="row-ico amber"><Clock size={16} /></div>
                  <div className="row-details">
                    <strong>Pending Leave Requests ({summary.pending_leave_requests})</strong>
                    <p>Review and approve employee vacation and sick leave applications.</p>
                  </div>
                  <Link to="/hr/employees" className="action-btn-sm">Review →</Link>
                </div>

                <div className="action-row">
                  <div className="row-ico teal"><TriangleAlert size={16} /></div>
                  <div className="row-details">
                    <strong>Open Complaints & Inquiries ({summary.open_complaints})</strong>
                    <p>Address reported workplace concerns and staff requests.</p>
                  </div>
                  <Link to="/hr/employees" className="action-btn-sm">Inspect →</Link>
                </div>

                <div className="action-row">
                  <div className="row-ico indigo"><Users size={16} /></div>
                  <div className="row-details">
                    <strong>Employee Profile Directory ({summary.total_employees})</strong>
                    <p>Manage employee records, onboard new hires, and update designations.</p>
                  </div>
                  <Link to="/hr/employees" className="action-btn-sm">Open Directory →</Link>
                </div>

                <div className="action-row">
                  <div className="row-ico purple"><FolderKanban size={16} /></div>
                  <div className="row-details">
                    <strong>Sprint Project Allocations ({summary.active_projects})</strong>
                    <p>Define project roles and assign employees to ongoing initiatives.</p>
                  </div>
                  <Link to="/hr/projects" className="action-btn-sm">Manage Projects →</Link>
                </div>
              </div>
            </div>

            {/* Employee Overview & Headcount */}
            <div className="enterprise-panel">
              <div className="panel-header-row">
                <div className="panel-title-wrap">
                  <TrendingUp size={18} className="text-emerald" />
                  <h3>Employee Overview</h3>
                </div>
                <Link to="/hr/employees" className="link-action-btn">Directory View →</Link>
              </div>

              <div className="employee-stat-breakdown-grid">
                <div className="breakdown-box">
                  <span className="breakdown-lbl">Total Headcount</span>
                  <strong className="breakdown-val">{summary.total_employees}</strong>
                </div>
                <div className="breakdown-box">
                  <span className="breakdown-lbl">Active Roster</span>
                  <strong className="breakdown-val text-green">{summary.active_employees}</strong>
                </div>
                <div className="breakdown-box">
                  <span className="breakdown-lbl">Inactive / Notice</span>
                  <strong className="breakdown-val text-muted">{summary.inactive_employees}</strong>
                </div>
                <div className="breakdown-box">
                  <span className="breakdown-lbl">On Leave Today</span>
                  <strong className="breakdown-val text-amber">{summary.on_leave_today}</strong>
                </div>
              </div>

              <div className="recent-hires-section">
                <h4>Recently Joined Personnel</h4>
                {summary.recent_employees && summary.recent_employees.length > 0 ? (
                  <div className="recent-hires-list">
                    {summary.recent_employees.map((emp) => (
                      <div key={emp.id} className="recent-hire-row">
                        <div className="hire-avatar">
                          {emp.profile_photo_url ? (
                            <img src={emp.profile_photo_url} alt={emp.first_name} />
                          ) : (
                            emp.first_name.charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="hire-details">
                          <strong>{emp.first_name} {emp.last_name}</strong>
                          <small>{emp.designation ? `${emp.designation} • ` : ""}{emp.email} • {emp.employee_code}</small>
                        </div>
                        <span className="status-pill active">{emp.employment_status}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state-card mini">
                    <p>No new employee onboarding records logged yet.</p>
                    <button
                      type="button"
                      onClick={() => setCreateEmployeeModalOpen(true)}
                      className="empty-cta-link"
                      style={{ background: "none", border: "none", cursor: "pointer", font: "inherit" }}
                    >
                      + Onboard First Employee
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ================= ACTIVE PROJECTS OVERVIEW ================= */}
          <div className="enterprise-panel" style={{ marginTop: "24px" }}>
            <div className="panel-header-row">
              <div className="panel-title-wrap">
                <FolderKanban size={18} className="text-emerald" />
                <h3>Active Projects Overview</h3>
              </div>
              <Link to="/hr/projects" className="link-action-btn">View Projects →</Link>
            </div>

            {summary.active_projects_list && summary.active_projects_list.length > 0 ? (
              <div className="table-responsive-box">
                <table className="ent-table-styled">
                  <thead>
                    <tr>
                      <th>Project Code</th>
                      <th>Project Name</th>
                      <th>Status</th>
                      <th>Owner / Manager</th>
                      <th>Staff Count</th>
                      <th>Roles</th>
                      <th>Start Date</th>
                      <th>Expected End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.active_projects_list.map((proj) => (
                      <tr key={proj.id}>
                        <td><span className="code-pill">{proj.project_code}</span></td>
                        <td><strong>{proj.project_name}</strong></td>
                        <td>
                          <span className={`status-pill ${proj.status.toLowerCase()}`}>
                            {proj.status}
                          </span>
                        </td>
                        <td>{proj.project_manager || "Admin"}</td>
                        <td>{proj.employees_count} Members</td>
                        <td>{proj.roles_count} Roles</td>
                        <td>{proj.start_date || "—"}</td>
                        <td>{proj.expected_end_date || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state-card">
                <FolderKanban size={40} className="empty-ico text-emerald" />
                <h4>No Active Projects Registered</h4>
                <p>Projects configured by HR will display status telemetry, assigned teams, and sprint timelines here.</p>
                <Link to="/hr/projects" className="hero-cta-btn primary" style={{ marginTop: "12px", display: "inline-flex" }}>
                  <Plus size={16} /> Create Enterprise Project
                </Link>
              </div>
            )}
          </div>

        </main>
      </div>

      {/* Reusable Enterprise Create Employee Modal (Single Source of Truth) */}
      <CreateEmployeeModal
        isOpen={createEmployeeModalOpen}
        onClose={() => setCreateEmployeeModalOpen(false)}
        onSuccess={handleDashboardEmployeeCreated}
      />
    </div>
  );
}