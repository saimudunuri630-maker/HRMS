import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { 
  FolderKanban, 
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
  Clock, 
  CheckCircle2, 
  AlertCircle,
  User,
  ExternalLink,
  Award,
  Layers,
  ArrowRight,
  ShieldAlert
} from "lucide-react";
import { authService, dashboardService, attendanceService } from "../services/api";
import { broadcastChannel } from "../services/authSync";
import ProfileDropdown from "../components/ProfileDropdown";
import "../styles/EmployeeDashboard.css";

export default function EmployeeDashboard({ onToggleSidebar }) {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          name: parsed.full_name || (parsed.first_name ? `${parsed.first_name} ${parsed.last_name || ""}`.trim() : parsed.email?.split("@")[0] || "Staff Member"),
          email: parsed.email || "",
          role: "EMPLOYEE",
          employee_code: parsed.employee_code || "",
          photo: parsed.profile_photo_url || null,
        };
      }
    } catch {}
    return {
      name: "Staff Member",
      email: "",
      role: "EMPLOYEE",
      employee_code: "",
      photo: null,
    };
  });

  const [summary, setSummary] = useState({
    employee_id: null,
    employee_code: "",
    employee_name: "Staff Member",
    email: "",
    role: "EMPLOYEE",
    my_projects_count: 0,
    my_active_projects: 0,
    my_completed_projects: 0,
    today_attendance_status: "NOT_CLOCKED_IN",
    today_clock_in_time: null,
    leave_balance: 0,
    pending_leave_requests: 0,
    pending_work_reports: 0,
    unread_notifications: 0,
    assigned_projects: [],
    recent_announcements: [],
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
  const [clockActionLoading, setClockActionLoading] = useState(false);
  const [clockMessage, setClockMessage] = useState("");

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

  // Fetch Live Employee Data
  const loadDashboardData = async () => {
    try {
      const [meData, sumData] = await Promise.all([
        authService.getMe().catch(() => null),
        dashboardService.getEmployeeDashboardSummary(),
      ]);

      if (meData) {
        setCurrentUser({
          name: meData.full_name || (meData.first_name ? `${meData.first_name} ${meData.last_name || ""}`.trim() : meData.email.split("@")[0]),
          email: meData.email,
          role: "EMPLOYEE",
          employee_code: meData.employee_code || sumData?.employee_code || "",
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
      console.error("Employee dashboard data error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();

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

  // Handle Login / Logout
  const handleClockToggle = async () => {
    setClockActionLoading(true);
    setClockMessage("");

    try {
      if (summary.today_attendance_status === "NOT_CLOCKED_IN") {
        await attendanceService.checkIn("Logged in via Staff Portal");
        setClockMessage("Successfully Logged In for today!");
      } else if (summary.today_attendance_status === "CLOCKED_IN") {
        await attendanceService.checkOut("Completed daily shift");
        setClockMessage("Successfully Logged Out. Have a great evening!");
      }
      await loadDashboardData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setClockMessage(typeof detail === "string" ? detail : "Attendance action completed.");
    } finally {
      setClockActionLoading(false);
      setTimeout(() => setClockMessage(""), 5000);
    }
  };

  const handleSignOut = () => {
    authService.logout();
  };

  return (
    <div className="emp-enterprise-layout">
      {/* ================= MAIN CONTENT WRAPPER ================= */}
      <div className="emp-main-content-wrapper">
        
        {/* Top Header */}
        <header className="enterprise-top-header">
          <div className="header-left-group">
            {onToggleSidebar && (
              <button className="mobile-menu-toggle" onClick={onToggleSidebar} aria-label="Open menu">
                <Menu size={20} />
              </button>
            )}
            <div className="header-breadcrumb">
              <span>Staff Portal</span>
              <span className="sep">/</span>
              <span className="current">Personal Command Desk</span>
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
              onClick={() => navigate("/employee/notifications")}
              id="btn-employee-notifications"
              aria-label="Notifications"
            >
              <Bell size={18} />
              {unreadCount > 0 && (
                <span className="notif-dot" id="employee-notif-dot" aria-hidden="true" />
              )}
            </button>

            <ProfileDropdown 
              currentUser={currentUser} 
              role="employee" 
              employeeCode={summary.employee_code || currentUser.employee_code} 
            />
          </div>
        </header>

        {/* Workspace Body */}
        <main className="emp-command-workspace">
          
          {/* Hero Banner with Clock-in Widget */}
          <div className="emp-hero-banner">
            <div>
              <h1>{greeting}, {currentUser.name}</h1>
              <p>Welcome to your personal self-service portal. Track assignments, manage leave, and log shift telemetry.</p>
            </div>

            <div className="emp-clock-widget">
              <div className="clock-status-pill">
                <span className={`status-dot ${summary.today_attendance_status.toLowerCase()}`}>●</span>
                <span className="clock-status-text">
                  {summary.today_attendance_status === "CLOCKED_IN"
                    ? `Logged In (${summary.today_clock_in_time || "Today"})`
                    : summary.today_attendance_status === "CLOCKED_OUT"
                    ? "Shift Finished (Logged Out)"
                    : "Not Logged In Today"}
                </span>
              </div>

              {summary.today_attendance_status !== "CLOCKED_OUT" && (
                <button 
                  className={`btn-clock-action ${summary.today_attendance_status === "CLOCKED_IN" ? "clock-out" : "clock-in"}`}
                  onClick={handleClockToggle}
                  disabled={clockActionLoading}
                >
                  <Clock size={15} />
                  <span>
                    {clockActionLoading 
                      ? "Recording..." 
                      : summary.today_attendance_status === "CLOCKED_IN" 
                      ? "Logout" 
                      : "Login Now"}
                  </span>
                </button>
              )}
            </div>
          </div>

          {clockMessage && (
            <div className="emp-notice-banner success">
              <CheckCircle2 size={16} />
              <span>{clockMessage}</span>
            </div>
          )}

          {/* ================= EMPLOYEE KPI CARDS ================= */}
          <div className="emp-kpi-grid">
            <div className="kpi-card-ent emerald">
              <div className="kpi-top-row">
                <span>MY PROJECTS</span>
                <FolderKanban size={18} className="ico-emerald" />
              </div>
              <h2>{loading ? "..." : summary.my_projects_count}</h2>
              <small className="kpi-sub positive">
                {summary.my_projects_count === 1 ? "1 assigned project" : `${summary.my_projects_count} assigned projects`}
              </small>
            </div>

            <div className="kpi-card-ent blue">
              <div className="kpi-top-row">
                <span>ACTIVE PROJECTS</span>
                <Layers size={18} className="ico-blue" />
              </div>
              <h2>{loading ? "..." : summary.my_active_projects}</h2>
              <small className="kpi-sub positive">In sprint delivery</small>
            </div>

            <div className="kpi-card-ent slate">
              <div className="kpi-top-row">
                <span>COMPLETED</span>
                <CheckCircle2 size={18} className="ico-slate" />
              </div>
              <h2>{loading ? "..." : summary.my_completed_projects}</h2>
              <small className="kpi-sub">Finished initiatives</small>
            </div>

            <div className="kpi-card-ent amber">
              <div className="kpi-top-row">
                <span>LEAVE BALANCE</span>
                <CalendarDays size={18} className="ico-amber" />
              </div>
              <h2>{loading ? "..." : `${summary.leave_balance} Days`}</h2>
              <small className="kpi-sub">Annual paid quota</small>
            </div>

            <div className="kpi-card-ent purple">
              <div className="kpi-top-row">
                <span>PENDING LEAVES</span>
                <Clock size={18} className="ico-purple" />
              </div>
              <h2>{loading ? "..." : summary.pending_leave_requests}</h2>
              <small className="kpi-sub">Under review</small>
            </div>
          </div>

          {/* ================= SECTION: MY PROJECTS CARDS ================= */}
          <div className="enterprise-panel">
            <div className="panel-header-row">
              <div className="panel-title-wrap">
                <FolderKanban size={18} className="text-emerald" />
                <div>
                  <h3 style={{ margin: 0, fontSize: "16px" }}>My Projects</h3>
                  <span style={{ fontSize: "12px", color: "#64748b" }}>
                    You are currently assigned to {summary.my_projects_count} {summary.my_projects_count === 1 ? "project" : "projects"}.
                  </span>
                </div>
              </div>
              <Link to="/employee/projects" className="link-action-btn">
                All Projects <ArrowRight size={14} style={{ display: "inline", verticalAlign: "middle" }} />
              </Link>
            </div>

            {summary.assigned_projects && summary.assigned_projects.length > 0 ? (
              <div className="emp-projects-cards-grid">
                {summary.assigned_projects.map((proj) => (
                  <div key={proj.id} className="emp-project-kpi-card">
                    <div className="card-top-row">
                      <div className="proj-title-group">
                        <span className="code-pill">{proj.project_code}</span>
                        <h4>{proj.project_name}</h4>
                      </div>
                      <span className={`status-pill ${proj.status.toLowerCase()}`}>
                        ● {proj.status}
                      </span>
                    </div>

                    <div className="proj-details-row">
                      <div className="proj-detail-item">
                        <span className="label">My Role:</span>
                        <span className="role-value">{proj.role_name || "Role not assigned"}</span>
                      </div>
                      <div className="proj-detail-item">
                        <span className="label">Team Size:</span>
                        <span className="team-value">{proj.team_members_count || 1} members</span>
                      </div>
                    </div>

                    <div className="card-footer-action">
                      <Link to="/employee/projects" className="btn-view-proj">
                        View Project <ArrowRight size={13} />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state-card" style={{ padding: "30px", textAlign: "center" }}>
                <FolderKanban size={36} className="text-emerald" style={{ margin: "0 auto 10px" }} />
                <h4>No Projects Assigned to You Yet</h4>
                <p style={{ color: "#64748b", fontSize: "13px" }}>
                  When HR assigns you to a project and assigns your project role, it will appear here.
                </p>
              </div>
            )}
          </div>

          {/* ================= DUAL PANELS: MY PROJECT ROLES & ANNOUNCEMENTS ================= */}
          <div className="emp-dual-grid">
            
            {/* My Project Roles */}
            <div className="enterprise-panel">
              <div className="panel-header-row">
                <div className="panel-title-wrap">
                  <Award size={18} className="text-emerald" />
                  <div>
                    <h3 style={{ margin: 0, fontSize: "15px" }}>My Project Roles</h3>
                    <span style={{ fontSize: "11.5px", color: "#64748b" }}>Functional role designations per assignment</span>
                  </div>
                </div>
                <span className="badge-pill">{summary.assigned_projects?.length || 0} Assignments</span>
              </div>

              {summary.assigned_projects && summary.assigned_projects.length > 0 ? (
                <div className="roles-stack-list">
                  {summary.assigned_projects.map((proj) => (
                    <div key={proj.id} className="role-summary-card">
                      <div>
                        <div className="role-proj-name">{proj.project_name}</div>
                        <span className="role-proj-code">{proj.project_code} • {proj.status}</span>
                      </div>
                      <div>
                        {proj.role_name && proj.role_name !== "Role not assigned" ? (
                          <span className="role-badge-assigned">{proj.role_name}</span>
                        ) : (
                          <span className="role-badge-unassigned">Role not assigned</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state-card" style={{ padding: "20px", textAlign: "center" }}>
                  <p className="no-items-text">No project role allocations recorded.</p>
                </div>
              )}
            </div>

            {/* Company Announcements */}
            <div className="enterprise-panel">
              <div className="panel-header-row">
                <div className="panel-title-wrap">
                  <Megaphone size={18} className="text-emerald" />
                  <h3>Company Announcements</h3>
                </div>
                <span className="badge-pill">Internal Feed</span>
              </div>

              <div className="announcements-stack">
                {summary.recent_announcements && summary.recent_announcements.length > 0 ? (
                  summary.recent_announcements.map((item) => (
                    <article key={item.id} className="announcement-item">
                      <div className="announcement-header">
                        <strong>{item.title}</strong>
                        <span className="announcement-date">{item.created_at}</span>
                      </div>
                      <p>{item.content}</p>
                    </article>
                  ))
                ) : (
                  <p className="no-items-text">No company notices posted at this time.</p>
                )}
              </div>
            </div>

          </div>

          {/* Policy / Governance Notice */}
          <div className="emp-role-notice-card">
            <ShieldAlert size={18} className="text-emerald flex-shrink-0" />
            <div>
              <strong>Employee Workspace Authorization Policy</strong>
              <p>
                Staff accounts have self-service access to personal profiles, assigned project sprint logs, 
                biometric attendance, and leave management. All project governance, employee directory mutations, 
                and role allocations are guarded and reserved for HR Administration.
              </p>
            </div>
          </div>

        </main>
      </div>
    </div>
  );
}