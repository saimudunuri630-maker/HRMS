import axios from "axios";
import { broadcastMessage } from "./authSync";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Auto-attach JWT token to all outgoing requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token") || localStorage.getItem("hrms_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercept 401 Unauthorized to clear invalid sessions
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isAuthRequest = error.config.url.includes("/login") || error.config.url.includes("/verify");
      if (!isAuthRequest) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        localStorage.removeItem("hrms_token");
        localStorage.removeItem("hrms_user");
        if (window.location.pathname !== "/login" && window.location.pathname !== "/" && window.location.pathname !== "/welcome") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ============================================================
// AUTHENTICATION SERVICES
// ============================================================

export const authService = {
  requestLoginOtp: async (email) => {
    const response = await api.post("/auth/login", { email: email.trim().toLowerCase() });
    return response.data;
  },

  verifyOtpCode: async (email, otp) => {
    const response = await api.post("/auth/verify-otp", {
      email: email.trim().toLowerCase(),
      otp: otp.trim(),
    });
    const data = response.data;

    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("hrms_token", data.access_token);
    }

    // Always fetch fresh user from /api/auth/me to ensure authoritative backend role
    try {
      const meRes = await api.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.data) {
        data.user = meRes.data;
        localStorage.setItem("user", JSON.stringify(meRes.data));
        localStorage.setItem("hrms_user", JSON.stringify(meRes.data));
      }
    } catch {
      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
        localStorage.setItem("hrms_user", JSON.stringify(data.user));
      }
    }

    broadcastMessage("AUTH_LOGIN", { user: data.user, token: data.access_token });
    return data;
  },

  resendLoginOtp: async (email) => {
    const response = await api.post("/auth/resend-otp", { email: email.trim().toLowerCase() });
    return response.data;
  },

  getMe: async () => {
    const response = await api.get("/api/auth/me");
    if (response.data) {
      localStorage.setItem("user", JSON.stringify(response.data));
      localStorage.setItem("hrms_user", JSON.stringify(response.data));
    }
    return response.data;
  },

  logout: async () => {
    try {
      await api.post("/auth/logout").catch(() => {});
    } finally {
      // Clear all authentication credentials & user session state
      // without blindly wiping non-auth settings
      const authKeys = [
        "token",
        "hrms_token",
        "user",
        "hrms_user",
        "auth_email",
        "currentUser",
        "session",
        "role",
      ];
      authKeys.forEach((key) => {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
      });
      broadcastMessage("AUTH_LOGOUT");
      window.location.href = "/login";
    }
  },
};

// ============================================================
// DASHBOARD SERVICES
// ============================================================

export const dashboardService = {
  getHrDashboardSummary: async () => {
    const response = await api.get("/api/hr/dashboard/summary");
    return response.data;
  },

  getEmployeeDashboardSummary: async () => {
    const response = await api.get("/api/employee/dashboard/summary");
    return response.data;
  },
};

// ============================================================
// PROFILE SERVICES
// ============================================================

export const profileService = {
  getMyProfile: async () => {
    const response = await api.get("/api/profile/me");
    return response.data;
  },

  updateMyProfile: async (data) => {
    const response = await api.put("/api/profile/me", data);
    return response.data;
  },

  uploadMyPhoto: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("/api/profile/me/photo", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },
};

// ============================================================
// EMPLOYEE MANAGEMENT SERVICES (HR ONLY)
// ============================================================

export const employeeService = {
  listEmployees: async (params = {}) => {
    const response = await api.get("/api/employees", { params });
    return response.data;
  },

  getEmployee: async (id) => {
    const response = await api.get(`/api/employees/${id}`);
    return response.data;
  },

  createEmployee: async (data) => {
    const response = await api.post("/api/employees", data);
    return response.data;
  },

  updateEmployee: async (id, data) => {
    const response = await api.put(`/api/employees/${id}`, data);
    return response.data;
  },

  activateEmployee: async (id) => {
    const response = await api.patch(`/api/employees/${id}/activate`);
    return response.data;
  },

  deactivateEmployee: async (id) => {
    const response = await api.patch(`/api/employees/${id}/deactivate`);
    return response.data;
  },

  removeEmployee: async (id) => {
    const response = await api.delete(`/api/employees/${id}`);
    return response.data;
  },
};

// ============================================================
// PROJECT SERVICES
// ============================================================

export const projectService = {
  listProjects: async (params = {}) => {
    const response = await api.get("/api/projects", { params });
    return response.data;
  },

  getProject: async (id) => {
    const response = await api.get(`/api/projects/${id}`);
    return response.data;
  },

  createProject: async (data) => {
    const response = await api.post("/api/projects", data);
    return response.data;
  },

  updateProject: async (id, data) => {
    const response = await api.put(`/api/projects/${id}`, data);
    return response.data;
  },

  updateProjectStatus: async (id, status) => {
    const response = await api.patch(`/api/projects/${id}/status`, { status });
    return response.data;
  },

  updateProjectProgress: async (id, progress_percentage) => {
    const response = await api.patch(`/api/projects/${id}/progress`, { progress_percentage });
    return response.data;
  },

  getMetrics: async () => {
    const response = await api.get("/api/projects/metrics");
    return response.data;
  },

  // Roles
  listProjectRoles: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/roles`);
    return response.data;
  },

  createProjectRole: async (projectId, data) => {
    const response = await api.post(`/projects/${projectId}/roles`, data);
    return response.data;
  },

  updateProjectRole: async (projectId, roleId, data) => {
    const response = await api.put(`/projects/${projectId}/roles/${roleId}`, data);
    return response.data;
  },

  deleteProjectRole: async (projectId, roleId) => {
    const response = await api.delete(`/projects/${projectId}/roles/${roleId}`);
    return response.data;
  },

  // Members
  listProjectMembers: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/members`);
    return response.data;
  },

  getAvailableEmployees: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/available-employees`);
    return response.data;
  },

  assignMember: async (projectId, data) => {
    const response = await api.post(`/projects/${projectId}/members`, data);
    return response.data;
  },

  removeMember: async (projectId, employeeId) => {
    const response = await api.delete(`/projects/${projectId}/members/${employeeId}`);
    return response.data;
  },

  updateMemberRole: async (projectId, employeeId, projectRoleId) => {
    const response = await api.put(`/projects/${projectId}/members/${employeeId}/role`, {
      project_role_id: projectRoleId,
    });
    return response.data;
  },

  // Assignments
  assignEmployee: async (projectId, data) => {
    const response = await api.post(`/projects/${projectId}/assignments`, data);
    return response.data;
  },

  getAssignments: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/assignments`);
    return response.data;
  },

  removeAssignment: async (projectId, assignmentId) => {
    const response = await api.patch(`/projects/${projectId}/assignments/${assignmentId}/remove`);
    return response.data;
  },

  // Employee specific
  getMyProjects: async () => {
    const response = await api.get("/projects/my-projects");
    return response.data;
  },

  getMyProjectDetails: async (id) => {
    const response = await api.get(`/projects/my-projects/${id}`);
    return response.data;
  },

  getMyDashboardProjects: async () => {
    const response = await api.get("/projects/my-dashboard");
    return response.data;
  },

  getHrDashboardProjects: async () => {
    const response = await api.get("/projects/dashboard");
    return response.data;
  },
};

// ============================================================
// DEDICATED PROJECT ROLES SERVICE
// ============================================================

export const projectRoleService = {
  listRoles: async (params = {}) => {
    const response = await api.get("/project-roles", { params });
    return response.data;
  },

  createRole: async (data) => {
    const response = await api.post("/project-roles", data);
    return response.data;
  },

  getRole: async (id) => {
    const response = await api.get(`/project-roles/${id}`);
    return response.data;
  },

  updateRole: async (id, data) => {
    const response = await api.put(`/project-roles/${id}`, data);
    return response.data;
  },

  deleteRole: async (id) => {
    const response = await api.delete(`/project-roles/${id}`);
    return response.data;
  },

  assignEmployees: async (roleId, employeeIds, projectId = null, extraData = {}) => {
    const ids = Array.isArray(employeeIds) ? employeeIds : [employeeIds];
    const payload = { employee_ids: ids, ...extraData };
    if (projectId) {
      try {
        const response = await api.post(`/projects/${projectId}/roles/${roleId}/assignments`, payload);
        return response.data;
      } catch (err) {
        // If scoped route has parameter issue, fallback to direct role assignments route
        if (err.response?.status === 404) {
          const fallback = await api.post(`/project-roles/${roleId}/assignments`, payload);
          return fallback.data;
        }
        throw err;
      }
    }
    const response = await api.post(`/project-roles/${roleId}/assignments`, payload);
    return response.data;
  },

  getAssignedEmployees: async (roleId, projectId = null) => {
    if (projectId) {
      try {
        const response = await api.get(`/projects/${projectId}/roles/${roleId}/assignments`);
        return response.data;
      } catch (err) {
        if (err.response?.status === 404) {
          const fallback = await api.get(`/project-roles/${roleId}/assignments`);
          return fallback.data;
        }
        throw err;
      }
    }
    const response = await api.get(`/project-roles/${roleId}/assignments`);
    return response.data;
  },

  removeEmployee: async (roleId, assignmentId, projectId = null) => {
    if (projectId) {
      try {
        const response = await api.delete(`/projects/${projectId}/roles/${roleId}/assignments/${assignmentId}`);
        return response.data;
      } catch (err) {
        if (err.response?.status === 404) {
          const fallback = await api.delete(`/project-roles/${roleId}/assignments/${assignmentId}`);
          return fallback.data;
        }
        throw err;
      }
    }
    const response = await api.delete(`/project-roles/${roleId}/assignments/${assignmentId}`);
    return response.data;
  },
};


// ============================================================
// ANNOUNCEMENTS SERVICE
// ============================================================

export const announcementService = {
  listAnnouncements: async (params = {}) => {
    const response = await api.get("/api/announcements", { params });
    return response.data;
  },
  list: async (params = {}) => {
    const response = await api.get("/api/announcements", { params });
    return response.data;
  },

  getAnnouncement: async (id) => {
    const response = await api.get(`/api/announcements/${id}`);
    return response.data;
  },
  get: async (id) => {
    const response = await api.get(`/api/announcements/${id}`);
    return response.data;
  },

  createAnnouncement: async (data) => {
    const response = await api.post("/api/announcements", data);
    return response.data;
  },
  create: async (data) => {
    const response = await api.post("/api/announcements", data);
    return response.data;
  },

  updateAnnouncement: async (id, data) => {
    const response = await api.put(`/api/announcements/${id}`, data);
    return response.data;
  },
  update: async (id, data) => {
    const response = await api.put(`/api/announcements/${id}`, data);
    return response.data;
  },

  publishAnnouncement: async (id) => {
    const response = await api.post(`/api/announcements/${id}/publish`);
    return response.data;
  },
  publish: async (id) => {
    const response = await api.post(`/api/announcements/${id}/publish`);
    return response.data;
  },

  archiveAnnouncement: async (id) => {
    const response = await api.post(`/api/announcements/${id}/archive`);
    return response.data;
  },
  archive: async (id) => {
    const response = await api.post(`/api/announcements/${id}/archive`);
    return response.data;
  },
};

// ============================================================
// WORK REPORTS SERVICE
// ============================================================

export const workReportService = {
  createReport: async (data) => {
    const response = await api.post("/api/work-reports", data);
    return response.data;
  },
  create: async (data) => {
    const response = await api.post("/api/work-reports", data);
    return response.data;
  },

  listMyReports: async (params = {}) => {
    const response = await api.get("/api/work-reports/me", { params });
    return response.data;
  },

  getMyReport: async (id) => {
    const response = await api.get(`/api/work-reports/me/${id}`);
    return response.data;
  },

  updateMyReport: async (id, data) => {
    const response = await api.put(`/api/work-reports/me/${id}`, data);
    return response.data;
  },
  update: async (id, data) => {
    const response = await api.put(`/api/work-reports/me/${id}`, data);
    return response.data;
  },

  deleteMyReport: async (id) => {
    const response = await api.delete(`/api/work-reports/me/${id}`);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/api/work-reports/me/${id}`);
    return response.data;
  },

  submitMyReport: async (id) => {
    const response = await api.post(`/api/work-reports/me/${id}/submit`);
    return response.data;
  },
  submit: async (id) => {
    const response = await api.post(`/api/work-reports/me/${id}/submit`);
    return response.data;
  },

  listHrReports: async (params = {}) => {
    const response = await api.get("/api/work-reports/hr", { params });
    return response.data;
  },

  getHrReport: async (id) => {
    const response = await api.get(`/api/work-reports/hr/${id}`);
    return response.data;
  },
};

// ============================================================
// COMPLAINTS SERVICE
// ============================================================

export const complaintService = {
  createComplaint: async (data) => {
    const response = await api.post("/api/complaints", data);
    return response.data;
  },
  create: async (data) => {
    const response = await api.post("/api/complaints", data);
    return response.data;
  },

  listMyComplaints: async (params = {}) => {
    const response = await api.get("/api/complaints/me", { params });
    return response.data;
  },

  getMyComplaint: async (id) => {
    const response = await api.get(`/api/complaints/me/${id}`);
    return response.data;
  },

  listHrComplaints: async (params = {}) => {
    const response = await api.get("/api/complaints/hr", { params });
    return response.data;
  },

  getHrComplaint: async (id) => {
    const response = await api.get(`/api/complaints/hr/${id}`);
    return response.data;
  },

  addHrFeedback: async (id, data) => {
    const response = await api.post(`/api/complaints/hr/${id}/feedback`, data);
    return response.data;
  },
  provideFeedback: async (id, data) => {
    const response = await api.post(`/api/complaints/hr/${id}/feedback`, data);
    return response.data;
  },

  updateComplaintStatus: async (id, data) => {
    const response = await api.put(`/api/complaints/hr/${id}`, data);
    return response.data;
  },
};

// ============================================================
// ATTENDANCE SERVICES
// ============================================================

export const attendanceService = {
  checkIn: async (remarks = "") => {
    const response = await api.post("/api/attendance/check-in", { remarks });
    return response.data;
  },

  checkOut: async (remarks = "") => {
    const response = await api.post("/api/attendance/check-out", { remarks });
    return response.data;
  },

  getTodayAttendance: async () => {
    const response = await api.get("/api/attendance/me/today");
    return response.data;
  },

  getMyAttendance: async (params = {}) => {
    const response = await api.get("/api/attendance/me", { params });
    return response.data;
  },

  getMyAttendanceHistory: async (params = {}) => {
    const response = await api.get("/api/attendance/me/history", { params });
    return response.data;
  },

  getHrDailySummary: async (date = null) => {
    const params = date ? { date } : {};
    const response = await api.get("/api/attendance/hr/daily-summary", { params });
    return response.data;
  },

  getHrAttendanceList: async (params = {}) => {
    const response = await api.get("/api/attendance/hr", { params });
    return response.data;
  },
};

// ============================================================
// CONSOLIDATED LEAVE SERVICE (Domain Architecture)
// ============================================================

export const leaveService = {
  getLeaveTypes: async () => {
    const response = await api.get("/api/leave/types");
    return response.data;
  },

  createLeaveType: async (data) => {
    const response = await api.post("/api/leave/types", data);
    return response.data;
  },

  updateLeaveType: async (id, data) => {
    const response = await api.put(`/api/leave/types/${id}`, data);
    return response.data;
  },

  getMyBalances: async () => {
    const response = await api.get("/api/leave/balances");
    return response.data;
  },

  getEmployeeBalances: async (employeeId, year = null) => {
    const params = year ? { year } : {};
    const response = await api.get(`/api/leave/balances/${employeeId}`, { params });
    return response.data;
  },

  listRequests: async (params = {}) => {
    const response = await api.get("/api/leave/requests", { params });
    return response.data;
  },

  applyLeave: async (data) => {
    const response = await api.post("/api/leave/requests", data);
    return response.data;
  },

  getRequest: async (id) => {
    const response = await api.get(`/api/leave/requests/${id}`);
    return response.data;
  },

  approveRequest: async (id, reason = "") => {
    const response = await api.post(`/api/leave/requests/${id}/approve`, { reason });
    return response.data;
  },

  rejectRequest: async (id, reason = "") => {
    const response = await api.post(`/api/leave/requests/${id}/reject`, { reason });
    return response.data;
  },

  cancelRequest: async (id) => {
    const response = await api.post(`/api/leave/requests/${id}/cancel`);
    return response.data;
  },

  revokeRequest: async (id, reason = "") => {
    const response = await api.post(`/api/leave/requests/${id}/revoke`, { reason });
    return response.data;
  },
};

// ============================================================
// NOTIFICATIONS SERVICE
// ============================================================

export const notificationService = {
  listNotifications: async (params = {}) => {
    const response = await api.get("/api/notifications", { params });
    return response.data;
  },

  getUnreadCount: async () => {
    const response = await api.get("/api/notifications/unread-count");
    return response.data;
  },

  markAsRead: async (id) => {
    const response = await api.put(`/api/notifications/${id}/read`);
    return response.data;
  },

  markAllAsRead: async () => {
    const response = await api.put("/api/notifications/read-all");
    return response.data;
  },
};

// ============================================================
// AUDIT LOGS SERVICE (HR ONLY)
// ============================================================

export const auditService = {
  listAuditLogs: async (params = {}) => {
    const response = await api.get("/api/audit-logs", { params });
    return response.data;
  },

  getAuditLogDetail: async (id) => {
    const response = await api.get(`/api/audit-logs/${id}`);
    return response.data;
  },
};

export default api;
