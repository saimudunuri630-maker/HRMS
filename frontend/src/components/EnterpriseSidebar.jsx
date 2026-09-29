import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Users,
  User,
  FolderKanban,
  ShieldCheck,
  Megaphone,
  FileChartColumn,
  TriangleAlert,
  CalendarCheck,
  CalendarDays,
  History,
  Bell,
  LogOut,
  X,
  Award,
  Layers,
  Inbox,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { authService } from "../services/api";
import "../styles/EnterpriseSidebar.css";

export default function EnterpriseSidebar({
  role = "hr",
  sidebarOpen = false,
  setSidebarOpen = () => {},
  sidebarCollapsed = false,
  toggleSidebarCollapsed = () => {},
}) {
  const location = useLocation();
  const navigate = useNavigate();

  const isHr = String(role).toLowerCase() === "hr";

  const hrNavigationItems = [
    { label: "Dashboard", path: "/hr/dashboard", icon: Users },
    { label: "My Profile", path: "/hr/profile", icon: User },
    { label: "Employees", path: "/hr/employees", icon: Users },
    { label: "Projects", path: "/hr/projects", icon: FolderKanban },
    { label: "Project Roles", path: "/hr/project-roles", icon: ShieldCheck },
    { label: "Announcements", path: "/hr/announcements", icon: Megaphone },
    { label: "Work Reports", path: "/hr/work-reports", icon: FileChartColumn },
    { label: "Complaints", path: "/hr/complaints", icon: TriangleAlert },
    { label: "Attendance", path: "/hr/attendance", icon: CalendarCheck },
    { label: "Leave Management", path: "/hr/leave", icon: CalendarDays },
    { label: "Audit Logs", path: "/hr/audit-logs", icon: History },
    { label: "Notifications", path: "/hr/notifications", icon: Bell },
  ];

  const employeeNavigationItems = [
    { label: "Dashboard", path: "/employee/dashboard", icon: FolderKanban },
    { label: "My Profile", path: "/employee/profile", icon: User },
    { label: "My Projects", path: "/employee/projects", icon: Layers },
    { label: "My Attendance", path: "/employee/attendance", icon: CalendarCheck },
    { label: "My Leave", path: "/employee/leave", icon: CalendarDays },
    { label: "My Work Reports", path: "/employee/work-reports", icon: FileChartColumn },
    { label: "My Complaints", path: "/employee/complaints", icon: TriangleAlert },
    { label: "Announcements", path: "/employee/announcements", icon: Megaphone },
    { label: "Notifications", path: "/employee/notifications", icon: Bell },
  ];

  const navItems = isHr ? hrNavigationItems : employeeNavigationItems;

  const handleSignOut = () => {
    authService.logout();
  };

  const handleNavClick = () => {
    if (window.innerWidth <= 1024) {
      setSidebarOpen(false);
    }
  };

  // Auto-close sidebar on route navigation
  React.useEffect(() => {
    if (window.innerWidth <= 1024) {
      setSidebarOpen(false);
    }
  }, [location.pathname]);

  // Close on Escape key press
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && sidebarOpen) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  // Lock body scroll when mobile drawer is open
  React.useEffect(() => {
    if (sidebarOpen && window.innerWidth <= 1024) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  const storedUser = (() => {
    try {
      const u = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  })();

  const userEmail = storedUser?.email || (isHr ? "hr@mediatize.com" : "employee@mediatize.com");
  const userRoleLabel = (storedUser?.role || (isHr ? "HR" : "EMPLOYEE")).toUpperCase();

  return (
    <>
      {sidebarOpen && (
        <div 
          className="sidebar-backdrop-overlay" 
          onClick={() => setSidebarOpen(false)} 
          aria-hidden="true"
        />
      )}

      <aside className={`enterprise-fixed-sidebar ${sidebarOpen ? "open" : ""} ${sidebarCollapsed ? "collapsed" : ""}`}>
        {/* Brand Header */}
        <div className="sidebar-brand-box">
          <div className="brand-logo-badge" title="Mediatize HRMS">M</div>
          {!sidebarCollapsed && (
            <div className="brand-title">
              <h3>Mediatize</h3>
              <span>{isHr ? "Enterprise HRMS" : "Staff Portal"}</span>
            </div>
          )}

          {/* Desktop Collapse / Expand Toggle Button */}
          <button
            type="button"
            className="sidebar-collapse-toggle-btn"
            onClick={toggleSidebarCollapsed}
            title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            aria-label={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {sidebarCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>

          {/* Mobile Close Button */}
          <button 
            type="button"
            className="mobile-close-btn" 
            onClick={() => setSidebarOpen(false)} 
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Navigation */}
        <div className="sidebar-nav-scroll">
          {!sidebarCollapsed && (
            <div className="nav-section-label">
              {isHr ? "NAVIGATION" : "MY WORKSPACE"}
            </div>
          )}
          <ul className="sidebar-services-list">
            {navItems.map((item, idx) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== "/hr/dashboard" && item.path !== "/employee/dashboard" && location.pathname.startsWith(item.path));
              return (
                <li key={idx}>
                  <Link
                    to={item.path}
                    className={`service-link ${isActive ? "active" : ""}`}
                    onClick={handleNavClick}
                    title={item.label}
                    data-tooltip={item.label}
                  >
                    <Icon size={18} />
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Sidebar Footer with User Badge & Logout */}
        <div className="sidebar-footer-box">
          <div className="sidebar-user-pill" title={`${userEmail} (${userRoleLabel})`}>
            <div className="sidebar-user-avatar">
              {userRoleLabel === "HR" ? "HR" : "EM"}
            </div>
            {!sidebarCollapsed && (
              <div className="sidebar-user-info">
                <span className="sidebar-user-email" title={userEmail}>
                  {userEmail}
                </span>
                <span className="sidebar-user-role">{userRoleLabel}</span>
              </div>
            )}
          </div>
          <button 
            type="button"
            className="sidebar-logout-btn" 
            onClick={handleSignOut}
            title={sidebarCollapsed ? "Sign Out" : undefined}
            aria-label="Sign Out"
          >
            <LogOut size={16} /> {!sidebarCollapsed && <span>Sign Out</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
