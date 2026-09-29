import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, Bell } from "lucide-react";
import EnterpriseSidebar from "./EnterpriseSidebar";
import "../styles/EnterpriseLayout.css";

export default function EnterpriseLayout({ children, role = "hr" }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem("hrms_sidebar_collapsed") === "true";
    } catch {
      return false;
    }
  });

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("hrms_sidebar_collapsed", String(next));
      } catch (e) {
        console.error("Failed to save sidebar state", e);
      }
      return next;
    });
  };

  return (
    <div className="enterprise-layout-root">
      {/* ENTERPRISE FIXED / DRAWER SIDEBAR */}
      <EnterpriseSidebar
        role={role}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        sidebarCollapsed={sidebarCollapsed}
        toggleSidebarCollapsed={toggleSidebarCollapsed}
      />

      {/* MAIN VIEWPORT */}
      <div className={`enterprise-main-viewport ${sidebarCollapsed ? "collapsed" : ""}`}>
        {/* MOBILE TOPBAR - Visible only on mobile/tablet viewports (<= 1024px) */}
        <header className="enterprise-mobile-topbar" aria-label="Mobile Navigation Bar">
          <button
            type="button"
            className="enterprise-mobile-hamburger"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label="Open Navigation Menu"
            aria-expanded={sidebarOpen}
          >
            <Menu size={22} />
          </button>

          <div className="mobile-brand-group">
            <div className="brand-logo-badge-sm">M</div>
            <div className="brand-text-wrap">
              <span className="mobile-brand-title">Mediatize</span>
              <span className="mobile-brand-tag">{role === "hr" ? "Enterprise HRMS" : "Staff Portal"}</span>
            </div>
          </div>

          <div className="mobile-topbar-actions">
            <Link
              to={role === "hr" ? "/hr/notifications" : "/employee/notifications"}
              className="mobile-topbar-bell"
              aria-label="Notifications"
              title="System Notifications"
            >
              <Bell size={18} />
            </Link>
          </div>
        </header>

        {/* PAGE CONTENT */}
        <div className="enterprise-page-body">
          {React.isValidElement(children)
            ? React.cloneElement(children, {
                onToggleSidebar: () => setSidebarOpen((prev) => !prev),
                sidebarOpen,
              })
            : children}
        </div>
      </div>
    </div>
  );
}
