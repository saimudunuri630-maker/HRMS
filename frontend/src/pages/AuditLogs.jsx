import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  History,
  Shield,
  Search,
  Filter,
  Calendar,
  ArrowLeft,
  RefreshCw,
  Eye,
  X,
  FileText,
  User,
  Clock,
  Layers,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { auditService, authService } from "../services/api";
import EnterprisePagination from "../components/EnterprisePagination";
import "../styles/Modules.css";

export default function AuditLogs() {
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
    return { name: "HR Administrator", email: "", role: "HR", photo: null };
  });

  const [logs, setLogs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState("");

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [moduleFilter, setModuleFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Selected Log Detail Modal
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    const fetchMe = () => {
      authService.getMe().then((me) => {
        if (me) {
          setCurrentUser({
            name: me.full_name || (me.first_name ? `${me.first_name} ${me.last_name || ""}`.trim() : me.email.split("@")[0]),
            email: me.email,
            role: (me.role || "HR").toUpperCase(),
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

  const parseAuditDetails = (log) => {
    if (!log.new_value) return {};
    try {
      if (typeof log.new_value === "object") return log.new_value;
      return JSON.parse(log.new_value);
    } catch {
      return {};
    }
  };

  const formatTimeOnly = (dateStr) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "—";
    }
  };

  const fetchAuditLogs = async (targetPage = currentPage) => {
    setLoading(true);
    setErrorBanner("");
    try {
      const params = {
        page: targetPage,
        page_size: pageSize,
      };
      if (searchTerm.trim()) params.search = searchTerm.trim();
      if (moduleFilter !== "all") params.module = moduleFilter;
      if (actionFilter !== "all") params.action = actionFilter;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        params.end_date = end.toISOString();
      }

      const data = await auditService.listAuditLogs(params);
      setLogs(data.items || []);
      setTotalCount(data.total || 0);
      setCurrentPage(targetPage);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
      const detail = err.response?.data?.detail || "Failed to load audit records.";
      setErrorBanner(typeof detail === "string" ? detail : "Access restricted to authorized HR administrators.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs(1);
  }, [moduleFilter, actionFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchAuditLogs(1);
  };

  const handleResetFilters = () => {
    setSearchTerm("");
    setModuleFilter("all");
    setActionFilter("all");
    setStartDate("");
    setEndDate("");
    fetchAuditLogs(1);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      fetchAuditLogs(newPage);
    }
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getModuleBadge = (mod) => {
    const m = (mod || "").toUpperCase();
    if (m === "AUTHENTICATION") return { label: "AUTH", bg: "#eff6ff", text: "#1d4ed8" };
    if (m === "PROJECTS") return { label: "PROJECTS", bg: "#f0fdf4", text: "#15803d" };
    if (m === "LEAVE") return { label: "LEAVE", bg: "#fdf4ff", text: "#a21caf" };
    if (m === "ANNOUNCEMENTS") return { label: "ANNOUNCEMENT", bg: "#faf5ff", text: "#7e22ce" };
    if (m === "COMPLAINTS") return { label: "COMPLAINT", bg: "#fffbeb", text: "#b45309" };
    if (m === "ATTENDANCE") return { label: "ATTENDANCE", bg: "#ecfeff", text: "#0e7490" };
    if (m === "EMPLOYEE") return { label: "EMPLOYEE", bg: "#f1f5f9", text: "#334155" };
    return { label: m || "SYSTEM", bg: "#f1f5f9", text: "#475569" };
  };

  const getActionBadge = (action) => {
    const a = (action || "").toUpperCase();
    if (a === "LOGIN") return { bg: "#ecfdf5", text: "#065f46" };
    if (a === "LOGOUT") return { bg: "#f1f5f9", text: "#475569" };
    if (a.includes("FAILED") || a.includes("REJECT")) return { bg: "#fef2f2", text: "#991b1b" };
    if (a.includes("APPROV") || a.includes("CREATE")) return { bg: "#eff6ff", text: "#1d4ed8" };
    return { bg: "#f8fafc", text: "#334155" };
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="module-page-wrapper">
      {/* Top Header */}
      <header className="module-header-bar">
        <div className="module-header-container">
          <div className="module-header-left">
            <Link to="/hr/dashboard" className="module-back-btn">
              <ArrowLeft size={16} /> Back to Dashboard
            </Link>
            <div className="module-header-meta">
              <h2>Audit Logs</h2>
              <span>Enterprise immutable audit trails & compliance telemetry</span>
            </div>
          </div>

          <div className="module-header-right">
            <button
              onClick={() => fetchAuditLogs(currentPage)}
              disabled={loading}
              className="btn-secondary"
              title="Refresh audit logs"
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="module-main-container">
        {errorBanner && (
          <div className="module-alert-banner error">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertCircle size={18} />
              <span>{errorBanner}</span>
            </div>
            <button onClick={() => setErrorBanner("")}>×</button>
          </div>
        )}

        {/* Filter Controls Bar */}
        <div
          style={{
            background: "#ffffff",
            padding: "20px",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            marginBottom: "20px",
          }}
        >
          <form onSubmit={handleSearchSubmit}>
            <div className="audit-filter-grid">
              {/* Free text search */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Search Employee / Action
                </label>
                <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                  <Search size={15} style={{ position: "absolute", left: "12px", color: "#94a3b8" }} />
                  <input
                    type="text"
                    placeholder="Search employee name, action, or description..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "9px 12px 9px 36px",
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

              {/* Module Filter */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Module
                </label>
                <select
                  value={moduleFilter}
                  onChange={(e) => setModuleFilter(e.target.value)}
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
                  <option value="all">All Modules</option>
                  <option value="AUTHENTICATION">Authentication</option>
                  <option value="ATTENDANCE">Attendance</option>
                  <option value="PROJECTS">Projects</option>
                  <option value="LEAVE">Leave Management</option>
                  <option value="ANNOUNCEMENTS">Announcements</option>
                  <option value="COMPLAINTS">Complaints</option>
                  <option value="EMPLOYEE">Employee</option>
                  <option value="WORK_REPORTS">Work Reports</option>
                  <option value="SYSTEM">System</option>
                </select>
              </div>

              {/* Action Filter */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Action
                </label>
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
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
                  <option value="all">All Actions</option>
                  <option value="LOGIN">LOGIN</option>
                  <option value="LOGOUT">LOGOUT</option>
                  <option value="Attendance login">Attendance Login</option>
                  <option value="Attendance logout">Attendance Logout</option>
                  <option value="LOGIN_FAILED">LOGIN_FAILED</option>
                  <option value="Leave approved">Leave Approved</option>
                  <option value="Leave rejected">Leave Rejected</option>
                  <option value="Leave request created">Leave Request Created</option>
                  <option value="Project created">Project Created</option>
                  <option value="Announcement published">Announcement Published</option>
                </select>
              </div>

              {/* Start Date */}
              <div style={{ minWidth: 0 }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
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
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
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
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={handleResetFilters}
                className="btn-secondary"
                style={{ padding: "8px 16px", fontSize: "13px" }}
              >
                Reset
              </button>
              <button
                type="submit"
                className="btn-primary"
                style={{ padding: "8px 18px", fontSize: "13px" }}
              >
                <Search size={14} /> Filter Logs
              </button>
            </div>
          </form>
        </div>

        {/* Audit Logs Table */}
        <div
          style={{
            background: "#ffffff",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            overflow: "hidden",
            boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
          }}
        >
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #e2e8f0",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Shield size={18} style={{ color: "#2563eb" }} />
              <strong style={{ fontSize: "14px", color: "#0f172a" }}>Immutable Audit Records</strong>
              <span
                style={{
                  background: "#f1f5f9",
                  color: "#475569",
                  borderRadius: "12px",
                  padding: "2px 8px",
                  fontSize: "12px",
                  fontWeight: "600",
                }}
              >
                {totalCount} total events
              </span>
            </div>
          </div>

          <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
            <table style={{ width: "100%", minWidth: "860px", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
              <thead>
                <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0", color: "#475569" }}>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Date & Time</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Employee / User</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Role</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Module</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Action</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Login Time</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Logout Time</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600" }}>Description</th>
                  <th style={{ padding: "12px 14px", fontWeight: "600", textAlign: "center" }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: "center", padding: "60px 20px", color: "#64748b" }}>
                      <div className="spin" style={{ display: "inline-block", marginBottom: "8px" }}>
                        <RefreshCw size={24} />
                      </div>
                      <p style={{ margin: 0 }}>Loading audit records...</p>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: "center", padding: "60px 20px", color: "#64748b" }}>
                      <History size={40} style={{ color: "#cbd5e1", margin: "0 auto 12px auto" }} />
                      <p style={{ margin: 0, fontWeight: "600" }}>No audit log entries found</p>
                      <small>Try clearing or adjusting your search filters.</small>
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => {
                    const modBadge = getModuleBadge(log.module);
                    const actBadge = getActionBadge(log.action);
                    const details = parseAuditDetails(log);
                    const isLogin = log.action?.toUpperCase().includes("LOGIN");
                    const isLogout = log.action?.toUpperCase().includes("LOGOUT");
                    const loginTime = details.login_time || (isLogin ? formatTimeOnly(log.created_at) : null);
                    const logoutTime = details.logout_time || (isLogout ? formatTimeOnly(log.created_at) : null);

                    return (
                      <tr
                        key={log.id}
                        style={{
                          borderBottom: "1px solid #f1f5f9",
                          transition: "background 0.1s ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                      >
                        {/* Date & Time */}
                        <td style={{ padding: "12px 14px", color: "#64748b", whiteSpace: "nowrap", fontSize: "12px" }}>
                          {formatDateTime(log.created_at)}
                        </td>

                        {/* User */}
                        <td style={{ padding: "12px 14px", color: "#0f172a", fontWeight: "600" }}>
                          <div>{log.user_name || "System"}</div>
                          {log.user_email && (
                            <div style={{ fontSize: "11px", color: "#64748b", fontWeight: "400" }}>
                              {log.user_email}
                            </div>
                          )}
                        </td>

                        {/* Role */}
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: "700",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: log.user_role === "HR" ? "#eff6ff" : "#f1f5f9",
                              color: log.user_role === "HR" ? "#1d4ed8" : "#475569",
                            }}
                          >
                            {log.user_role || "SYSTEM"}
                          </span>
                        </td>

                        {/* Module */}
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: "700",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: modBadge.bg,
                              color: modBadge.text,
                            }}
                          >
                            {modBadge.label}
                          </span>
                        </td>

                        {/* Action */}
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: "600",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: actBadge.bg,
                              color: actBadge.text,
                              whiteSpace: "nowrap",
                            }}
                          >
                            {log.action}
                          </span>
                        </td>

                        {/* Login Time */}
                        <td style={{ padding: "12px 14px", fontSize: "12px", whiteSpace: "nowrap" }}>
                          {loginTime ? (
                            <span style={{ color: "#16a34a", fontWeight: "600" }}>{loginTime}</span>
                          ) : (
                            <span style={{ color: "#94a3b8" }}>—</span>
                          )}
                        </td>

                        {/* Logout Time */}
                        <td style={{ padding: "12px 14px", fontSize: "12px", whiteSpace: "nowrap" }}>
                          {logoutTime ? (
                            <span style={{ color: "#dc2626", fontWeight: "600" }}>{logoutTime}</span>
                          ) : (
                            <span style={{ color: "#94a3b8" }}>—</span>
                          )}
                        </td>

                        {/* Description */}
                        <td style={{ padding: "12px 14px", color: "#334155", maxWidth: "280px", wordBreak: "break-word", fontSize: "12px" }}>
                          {log.description}
                        </td>

                        {/* Action Button: View Details (No Edit, No Delete) */}
                        <td style={{ padding: "12px 14px", textAlign: "center" }}>
                          <button
                            onClick={() => setSelectedLog(log)}
                            className="btn-secondary"
                            style={{ padding: "5px 10px", fontSize: "11px" }}
                            title="Inspect audit details"
                          >
                            <Eye size={13} /> View
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <EnterprisePagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={totalCount}
            pageSize={pageSize}
            itemLabel="audit logs"
            onPageChange={handlePageChange}
            standalone={false}
          />
        </div>
      </main>

      {/* Modal: View Audit Log Details */}
      {selectedLog && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
          onClick={() => setSelectedLog(null)}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "12px",
              maxWidth: "600px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
              border: "1px solid #e2e8f0",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: "18px 24px",
                borderBottom: "1px solid #e2e8f0",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Shield size={20} style={{ color: "#2563eb" }} />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>
                  Audit Record #{selectedLog.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b" }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div>
                <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>Action & Module</strong>
                <span style={{ fontWeight: "700", color: "#0f172a" }}>{selectedLog.action}</span>
                <span style={{ color: "#64748b", marginLeft: "8px" }}>in module {selectedLog.module}</span>
              </div>

              <div>
                <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>Actor / User</strong>
                <div style={{ color: "#0f172a" }}>{selectedLog.user_name || "System"} ({selectedLog.user_role || "SYSTEM"})</div>
                {selectedLog.user_email && <div style={{ color: "#64748b", fontSize: "12px" }}>{selectedLog.user_email}</div>}
              </div>

              <div>
                <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>Description</strong>
                <p style={{ margin: 0, color: "#334155", background: "#f8fafc", padding: "10px 12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  {selectedLog.description}
                </p>
              </div>

              {selectedLog.old_value && (
                <div>
                  <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>Previous Value (Old)</strong>
                  <pre style={{ margin: 0, background: "#fef2f2", color: "#991b1b", padding: "10px 12px", borderRadius: "8px", border: "1px solid #fecaca", fontSize: "12px", overflowX: "auto" }}>
                    {selectedLog.old_value}
                  </pre>
                </div>
              )}

              {selectedLog.new_value && (
                <div>
                  <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>New Value</strong>
                  <pre style={{ margin: 0, background: "#ecfdf5", color: "#065f46", padding: "10px 12px", borderRadius: "8px", border: "1px solid #a7f3d0", fontSize: "12px", overflowX: "auto" }}>
                    {selectedLog.new_value}
                  </pre>
                </div>
              )}

              <div>
                <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>Timestamp</strong>
                <div style={{ color: "#64748b" }}>{new Date(selectedLog.created_at).toLocaleString()}</div>
              </div>

              {selectedLog.ip_address && (
                <div>
                  <strong style={{ color: "#475569", display: "block", marginBottom: "4px" }}>IP Address</strong>
                  <div style={{ color: "#64748b" }}>{selectedLog.ip_address}</div>
                </div>
              )}
            </div>

            <div style={{ padding: "14px 24px", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "flex-end", background: "#f8fafc" }}>
              <button onClick={() => setSelectedLog(null)} className="btn-secondary" style={{ padding: "7px 16px" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
