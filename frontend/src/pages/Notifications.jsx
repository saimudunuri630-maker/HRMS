import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Check,
  Clock,
  ArrowLeft,
  FolderKanban,
  Megaphone,
  CalendarDays,
  TriangleAlert,
  Layers,
  Settings,
  RefreshCw,
  ExternalLink,
  Inbox,
  Filter,
} from "lucide-react";
import { notificationService, authService } from "../services/api";
import { broadcastNotificationCount } from "../services/authSync";
import EnterprisePagination from "../components/EnterprisePagination";
import "../styles/Modules.css";

export default function Notifications({ role: propRole }) {
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
  const userRolePrefix = isHr ? "hr" : "employee";

  const [notifications, setNotifications] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [notificationBanner, setNotificationBanner] = useState({ type: "", text: "" });

  // Pagination (10 per page as specified)
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 10;

  // Filters
  const [statusTab, setStatusTab] = useState("all"); // 'all' | 'unread' | 'read'
  const [typeFilter, setTypeFilter] = useState("all");

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

  const fetchNotifications = async (targetPage = currentPage) => {
    setLoading(true);
    try {
      const params = {
        page: targetPage,
        page_size: pageSize,
      };
      if (statusTab === "unread") params.is_read = false;
      if (statusTab === "read") params.is_read = true;
      if (typeFilter !== "all") params.type = typeFilter;

      const data = await notificationService.listNotifications(params);
      setNotifications(data.items || []);
      setTotalCount(data.total || 0);
      setUnreadCount(data.unread_count || 0);
      setTotalPages(data.total_pages || Math.ceil((data.total || 0) / pageSize) || 1);
      setCurrentPage(targetPage);
      broadcastNotificationCount(data.unread_count || 0);
    } catch (err) {
      console.error("Failed to load notifications:", err);
      setNotificationBanner({ type: "error", text: "Failed to fetch notifications from server." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications(1);
  }, [statusTab, typeFilter]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      fetchNotifications(newPage);
    }
  };

  const handleMarkAsRead = async (id, e) => {
    if (e) e.stopPropagation();
    setActionLoading(true);
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((prev) => {
        const next = Math.max(0, prev - 1);
        broadcastNotificationCount(next, -1);
        return next;
      });
      if (statusTab === "unread") {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkAllAsRead = async () => {
    if (unreadCount === 0) return;
    setActionLoading(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() })));
      setUnreadCount(0);
      broadcastNotificationCount(0, 0);
      if (statusTab === "unread") {
        fetchNotifications(1);
      }
      setNotificationBanner({ type: "success", text: "All notifications marked as read." });
    } catch (err) {
      console.error("Failed to mark all as read:", err);
      setNotificationBanner({ type: "error", text: "Could not mark all notifications as read." });
    } finally {
      setActionLoading(false);
    }
  };

  const handleNotificationClick = async (notif) => {
    if (!notif.is_read) {
      handleMarkAsRead(notif.id);
    }

    const type = (notif.notification_type || notif.entity_type || "").toUpperCase();
    if (type.includes("PROJECT")) {
      navigate(`/${userRolePrefix}/projects`);
    } else if (type.includes("ANNOUNCEMENT")) {
      navigate(`/${userRolePrefix}/announcements`);
    } else if (type.includes("LEAVE")) {
      navigate(`/${userRolePrefix}/leave`);
    } else if (type.includes("COMPLAINT")) {
      navigate(`/${userRolePrefix}/complaints`);
    } else if (type.includes("ATTENDANCE")) {
      navigate(`/${userRolePrefix}/attendance`);
    }
  };

  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} min${diffMin > 1 ? "s" : ""} ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? "s" : ""} ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  const getTypeIcon = (type) => {
    const t = (type || "").toUpperCase();
    if (t.includes("PROJECT")) return <FolderKanban size={18} className="text-blue-500" />;
    if (t.includes("ANNOUNCEMENT")) return <Megaphone size={18} className="text-purple-500" />;
    if (t.includes("LEAVE")) return <CalendarDays size={18} className="text-emerald-500" />;
    if (t.includes("COMPLAINT")) return <TriangleAlert size={18} className="text-amber-500" />;
    return <Bell size={18} className="text-slate-500" />;
  };

  const getTypeBadgeClass = (type) => {
    const t = (type || "").toUpperCase();
    if (t.includes("PROJECT")) return "badge-blue";
    if (t.includes("ANNOUNCEMENT")) return "badge-purple";
    if (t.includes("LEAVE")) return "badge-emerald";
    if (t.includes("COMPLAINT")) return "badge-amber";
    return "badge-gray";
  };

  const dashboardPath = isHr ? "/hr/dashboard" : "/employee/dashboard";

  return (
    <div className="module-page-wrapper">
      {/* Top Header */}
      <header className="module-header-bar">
        <div className="module-header-container">
          <div className="module-header-left">
            <Link to={dashboardPath} className="module-back-btn">
              <ArrowLeft size={16} /> Back to Dashboard
            </Link>
            <div className="module-header-meta">
              <h2>Notifications</h2>
              <span>In-app notifications and important alerts</span>
            </div>
          </div>

          <div className="module-header-right">
            <button
              onClick={handleMarkAllAsRead}
              disabled={unreadCount === 0 || actionLoading}
              className="btn-secondary"
              title="Mark all notifications as read"
            >
              <CheckCheck size={16} /> Mark All as Read
            </button>
            <button
              onClick={fetchNotifications}
              disabled={loading}
              className="btn-secondary"
              title="Refresh notifications"
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="module-main-container">
        {notificationBanner.text && (
          <div className={`module-alert-banner ${notificationBanner.type}`}>
            <span>{notificationBanner.text}</span>
            <button onClick={() => setNotificationBanner({ type: "", text: "" })}>×</button>
          </div>
        )}

        {/* Filter Toolbar */}
        <div className="module-actions-bar" style={{ background: "#ffffff", padding: "16px 20px", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          {/* Status Tabs */}
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              className={`module-tab-btn ${statusTab === "all" ? "active" : ""}`}
              onClick={() => setStatusTab("all")}
              style={{
                padding: "8px 16px",
                borderRadius: "8px",
                border: "1px solid",
                borderColor: statusTab === "all" ? "#047857" : "#cbd5e1",
                background: statusTab === "all" ? "#ecfdf5" : "#ffffff",
                color: statusTab === "all" ? "#047857" : "#475569",
                fontWeight: "600",
                fontSize: "13px",
                cursor: "pointer",
              }}
            >
              All
            </button>
            <button
              className={`module-tab-btn ${statusTab === "unread" ? "active" : ""}`}
              onClick={() => setStatusTab("unread")}
              style={{
                padding: "8px 16px",
                borderRadius: "8px",
                border: "1px solid",
                borderColor: statusTab === "unread" ? "#047857" : "#cbd5e1",
                background: statusTab === "unread" ? "#ecfdf5" : "#ffffff",
                color: statusTab === "unread" ? "#047857" : "#475569",
                fontWeight: "600",
                fontSize: "13px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              Unread
              {unreadCount > 0 && (
                <span
                  style={{
                    background: "#047857",
                    color: "#ffffff",
                    borderRadius: "10px",
                    padding: "1px 7px",
                    fontSize: "11px",
                    fontWeight: "700",
                  }}
                >
                  {unreadCount}
                </span>
              )}
            </button>
            <button
              className={`module-tab-btn ${statusTab === "read" ? "active" : ""}`}
              onClick={() => setStatusTab("read")}
              style={{
                padding: "8px 16px",
                borderRadius: "8px",
                border: "1px solid",
                borderColor: statusTab === "read" ? "#047857" : "#cbd5e1",
                background: statusTab === "read" ? "#ecfdf5" : "#ffffff",
                color: statusTab === "read" ? "#047857" : "#475569",
                fontWeight: "600",
                fontSize: "13px",
                cursor: "pointer",
              }}
            >
              Read
            </button>
          </div>

          {/* Type Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Filter size={15} style={{ color: "#64748b" }} />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="module-select"
              style={{ minWidth: "160px" }}
            >
              <option value="all">All Categories</option>
              <option value="PROJECT">Projects</option>
              <option value="ANNOUNCEMENT">Announcements</option>
              <option value="LEAVE">Leaves</option>
              <option value="COMPLAINT">Complaints</option>
              <option value="SYSTEM">System</option>
            </select>
          </div>
        </div>

        {/* Notifications List */}
        <div style={{ marginTop: "20px" }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: "60px 20px", color: "#64748b" }}>
              <div className="spin" style={{ display: "inline-block", marginBottom: "12px" }}>
                <RefreshCw size={24} />
              </div>
              <p>Loading notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "12px",
                padding: "60px 20px",
                textAlign: "center",
              }}
            >
              <Inbox size={48} style={{ color: "#94a3b8", margin: "0 auto 16px auto" }} />
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#1e293b", margin: "0 0 6px 0" }}>
                No notifications found
              </h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
                {statusTab === "unread"
                  ? "You have caught up with all notifications!"
                  : "There are no notifications matching your current filters."}
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  style={{
                    background: notif.is_read ? "#ffffff" : "#f8faff",
                    border: notif.is_read ? "1px solid #e2e8f0" : "1px solid #bfdbfe",
                    borderRadius: "10px",
                    padding: "16px 20px",
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: "16px",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    boxShadow: notif.is_read ? "none" : "0 2px 4px rgba(4,120,87,0.06)",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#a7f3d0")}
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.borderColor = notif.is_read ? "#e2e8f0" : "#a7f3d0")
                  }
                >
                  <div style={{ display: "flex", gap: "14px", alignItems: "flex-start", flex: 1 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: "700",
                            textTransform: "uppercase",
                            padding: "2px 8px",
                            borderRadius: "6px",
                            background: notif.is_read ? "#f1f5f9" : "#eff6ff",
                            color: notif.is_read ? "#475569" : "#1d4ed8",
                            letterSpacing: "0.03em",
                          }}
                        >
                          {notif.notification_type || "SYSTEM"}
                        </span>
                        <h4
                          style={{
                            margin: 0,
                            fontSize: "14px",
                            fontWeight: notif.is_read ? "600" : "700",
                            color: notif.is_read ? "#1e293b" : "#0f172a",
                          }}
                        >
                          {notif.title}
                        </h4>
                      </div>

                      <p
                        style={{
                          margin: "0 0 6px 0",
                          fontSize: "13px",
                          color: notif.is_read ? "#64748b" : "#334155",
                          lineHeight: "1.5",
                        }}
                      >
                        {notif.message}
                      </p>

                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#94a3b8" }}>
                        <Clock size={12} />
                        <span>{formatTimeAgo(notif.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {!notif.is_read && (
                      <button
                        onClick={(e) => handleMarkAsRead(notif.id, e)}
                        className="btn-secondary"
                        style={{ padding: "6px 10px", fontSize: "12px" }}
                        title="Mark as read"
                      >
                        <Check size={14} /> Mark as Read
                      </button>
                    )}
                    <span style={{ color: "#94a3b8", display: "inline-flex", alignItems: "center" }}>
                      <ExternalLink size={14} />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Bottom Pagination */}
          <EnterprisePagination
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={totalCount}
            pageSize={pageSize}
            itemLabel="notifications"
            onPageChange={handlePageChange}
            standalone={true}
          />
        </div>
      </main>
    </div>
  );
}
