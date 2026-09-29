import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import VerifyOTP from "./pages/VerifyOTP";
import HrDashboard from "./pages/HrDashboard";
import HrEmployees from "./pages/HrEmployees";
import HrProjects from "./pages/HrProjects";
import HrProjectRoles from "./pages/HrProjectRoles";
import EmployeeDashboard from "./pages/EmployeeDashboard";
import EmployeeProjects from "./pages/EmployeeProjects";

import Profile from "./pages/Profile";
import LeaveManagement from "./pages/LeaveManagement";
import Announcements from "./pages/Announcements";
import WorkReports from "./pages/WorkReports";
import Complaints from "./pages/Complaints";
import Attendance from "./pages/Attendance";
import Notifications from "./pages/Notifications";
import AuditLogs from "./pages/AuditLogs";
import { authService } from "./services/api";
import { broadcastChannel } from "./services/authSync";
import EnterpriseLayout from "./components/EnterpriseLayout";

export const getSession = () => {
  const token = localStorage.getItem("token") || localStorage.getItem("hrms_token");
  const storedUser = localStorage.getItem("user") || localStorage.getItem("hrms_user");
  if (!token || !storedUser || storedUser === "undefined") return null;
  try {
    return { token, user: JSON.parse(storedUser) };
  } catch {
    return null;
  }
};

function ProtectedRoute({ children, roleRequired }) {
  const session = getSession();
  if (!session) return <Navigate to="/login" replace />;

  const currentRole = String(session.user?.role || "").toLowerCase();
  if (roleRequired && currentRole !== roleRequired.toLowerCase()) {
    return <Navigate to={currentRole === "hr" ? "/hr/dashboard" : "/employee/dashboard"} replace />;
  }
  return children;
}

function PublicRoute({ children }) {
  const session = getSession();
  if (session && session.token && session.user) {
    const currentRole = String(session.user?.role || "").toLowerCase();
    return <Navigate to={currentRole === "hr" ? "/hr/dashboard" : "/employee/dashboard"} replace />;
  }
  return children;
}

function RootRoute() {
  const session = getSession();
  if (session && session.token && session.user) {
    const currentRole = String(session.user?.role || "").toLowerCase();
    return <Navigate to={currentRole === "hr" ? "/hr/dashboard" : "/employee/dashboard"} replace />;
  }
  return <Welcome />;
}

export default function App() {
  const [, setSessionState] = useState(getSession);

  useEffect(() => {
    // Validate session in background with backend if token exists
    const currentSession = getSession();
    if (currentSession && currentSession.token) {
      authService.getMe().catch((err) => {
        if (err?.response?.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          localStorage.removeItem("hrms_token");
          localStorage.removeItem("hrms_user");
          setSessionState(null);
          const path = window.location.pathname;
          const isPublic = path === "/" || path === "/welcome" || path === "/login" || path === "/verify-otp";
          if (!isPublic) {
            window.location.href = "/login";
          }
        }
      });
    }

    // 1. Cross-tab storage change listener
    const handleStorageChange = (e) => {
      if (
        e.key === "token" ||
        e.key === "hrms_token" ||
        e.key === "user" ||
        e.key === "hrms_user"
      ) {
        const fresh = getSession();
        setSessionState(fresh);

        const currentPath = window.location.pathname;
        const isPublic =
          currentPath === "/" ||
          currentPath === "/welcome" ||
          currentPath === "/login" ||
          currentPath === "/verify-otp";

        if (!fresh && !isPublic) {
          window.location.href = "/login";
        } else if (fresh && isPublic) {
          const role = String(fresh.user?.role || "").toLowerCase();
          window.location.href = role === "hr" ? "/hr/dashboard" : "/employee/dashboard";
        }
      }
    };

    // 2. BroadcastChannel cross-tab listener
    const handleBroadcast = (event) => {
      const data = event.data || {};
      if (data.type === "AUTH_LOGOUT") {
        setSessionState(null);
        const currentPath = window.location.pathname;
        const isPublic =
          currentPath === "/" ||
          currentPath === "/welcome" ||
          currentPath === "/login" ||
          currentPath === "/verify-otp";
        if (!isPublic) {
          window.location.href = "/login";
        }
      } else if (data.type === "AUTH_LOGIN") {
        const fresh = getSession();
        setSessionState(fresh);
        const currentPath = window.location.pathname;
        const isPublic =
          currentPath === "/" ||
          currentPath === "/welcome" ||
          currentPath === "/login" ||
          currentPath === "/verify-otp";
        if (isPublic && fresh) {
          const role = String(fresh.user?.role || "").toLowerCase();
          window.location.href = role === "hr" ? "/hr/dashboard" : "/employee/dashboard";
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    if (broadcastChannel) {
      broadcastChannel.addEventListener("message", handleBroadcast);
    }

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      if (broadcastChannel) {
        broadcastChannel.removeEventListener("message", handleBroadcast);
      }
    };
  }, []);

  return (
    <Router>
      <Routes>
        {/* PUBLIC ENTRY & AUTHENTICATION */}
        <Route path="/" element={<RootRoute />} />
        <Route
          path="/welcome"
          element={
            <PublicRoute>
              <Welcome />
            </PublicRoute>
          }
        />
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/verify-otp"
          element={
            <PublicRoute>
              <VerifyOTP />
            </PublicRoute>
          }
        />

        {/* HR WORKSPACE (STRICTLY ROLE: HR) */}
        <Route
          path="/hr/dashboard"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <HrDashboard />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/employees"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <HrEmployees />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/projects"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <HrProjects />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/project-roles"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <HrProjectRoles />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/hr/profile"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <Profile />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/leave"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <LeaveManagement role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/announcements"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <Announcements role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/work-reports"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <WorkReports role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/complaints"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <Complaints role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/attendance"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <Attendance role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/notifications"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <Notifications role="hr" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/hr/audit-logs"
          element={
            <ProtectedRoute roleRequired="hr">
              <EnterpriseLayout role="hr">
                <AuditLogs />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />

        {/* EMPLOYEE WORKSPACE (STRICTLY ROLE: EMPLOYEE) */}
        <Route
          path="/employee/dashboard"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <EmployeeDashboard />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/employee/projects"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <EmployeeProjects />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/profile"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <Profile />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/leave"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <LeaveManagement role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/announcements"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <Announcements role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/work-reports"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <WorkReports role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/complaints"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <Complaints role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/attendance"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <Attendance role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employee/notifications"
          element={
            <ProtectedRoute roleRequired="employee">
              <EnterpriseLayout role="employee">
                <Notifications role="employee" />
              </EnterpriseLayout>
            </ProtectedRoute>
          }
        />

        {/* BACKWARD COMPATIBILITY ALIASES */}
        <Route path="/dashboard/hr" element={<Navigate to="/hr/dashboard" replace />} />
        <Route path="/dashboard/employee" element={<Navigate to="/employee/dashboard" replace />} />
        <Route path="/employees" element={<Navigate to="/hr/employees" replace />} />
        <Route path="/projects" element={<Navigate to="/hr/projects" replace />} />
        <Route path="/project-roles" element={<Navigate to="/hr/project-roles" replace />} />

        <Route path="/profile" element={<Navigate to="/hr/profile" replace />} />
        <Route path="/leave" element={<Navigate to="/hr/leave" replace />} />
        <Route path="/announcements" element={<Navigate to="/hr/announcements" replace />} />
        <Route path="/work-reports" element={<Navigate to="/hr/work-reports" replace />} />
        <Route path="/complaints" element={<Navigate to="/hr/complaints" replace />} />
        <Route path="/attendance" element={<Navigate to="/hr/attendance" replace />} />
        <Route path="/notifications" element={<Navigate to="/hr/notifications" replace />} />
        <Route path="/audit-logs" element={<Navigate to="/hr/audit-logs" replace />} />

        {/* CATCH ALL */}
        <Route
          path="*"
          element={
            <PublicRoute>
              <Navigate to="/welcome" replace />
            </PublicRoute>
          }
        />
      </Routes>
    </Router>
  );
}