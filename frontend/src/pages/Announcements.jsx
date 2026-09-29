import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Megaphone,
  Plus,
  Send,
  Archive,
  Eye,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  X,
  Loader2,
  Calendar,
  AlertTriangle,
  Clock
} from "lucide-react";
import { announcementService, authService } from "../services/api";
import "../styles/Modules.css";

export default function Announcements({ role: propRole }) {
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

  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Filter states
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null);
  const [readAnnouncements, setReadAnnouncements] = useState(() => {
    try {
      const stored = localStorage.getItem("read_announcements");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Form state
  const [form, setForm] = useState({
    title: "",
    content: "",
    priority: "NORMAL",
  });

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

  const loadAnnouncements = async () => {
    setLoading(true);
    try {
      const data = await announcementService.list();
      setAnnouncements(Array.isArray(data) ? data : (data?.items || []));
    } catch (err) {
      console.error("Failed to load announcements:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to load announcements." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnnouncements();
  }, []);

  // Save read announcement in local state
  const handleOpenAnnouncement = (item) => {
    setSelectedAnnouncement(item);
    if (!readAnnouncements.includes(item.id)) {
      const updated = [...readAnnouncements, item.id];
      setReadAnnouncements(updated);
      try {
        localStorage.setItem("read_announcements", JSON.stringify(updated));
      } catch {}
    }
  };

  // Create announcement (as Draft or Published)
  const handleCreate = async (asPublish = false) => {
    if (!form.title.trim()) {
      setNotification({ type: "error", text: "Announcement title is required." });
      return;
    }
    if (!form.content.trim()) {
      setNotification({ type: "error", text: "Announcement content is required." });
      return;
    }

    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      const created = await announcementService.create({
        title: form.title.trim(),
        content: form.content.trim(),
        priority: form.priority,
      });

      if (asPublish && created?.id) {
        await announcementService.publish(created.id);
        setNotification({
          type: "success",
          text: "Announcement published and broadcasted to all active employees via email & in-app notifications!",
        });
      } else {
        setNotification({
          type: "success",
          text: "Announcement saved as Draft.",
        });
      }

      setShowCreateModal(false);
      setForm({ title: "", content: "", priority: "NORMAL" });
      await loadAnnouncements();
    } catch (err) {
      console.error("Create announcement error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to create announcement." });
    } finally {
      setSubmitting(false);
    }
  };

  // Publish existing draft
  const handlePublish = async (id, title) => {
    if (!window.confirm(`Publish "${title}" to all active employees now? They will receive an email and in-app notification.`)) {
      return;
    }

    setSubmitting(true);
    try {
      await announcementService.publish(id);
      setNotification({
        type: "success",
        text: `Announcement "${title}" published and delivered to all active employees!`,
      });
      await loadAnnouncements();
    } catch (err) {
      console.error("Publish error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to publish announcement." });
    } finally {
      setSubmitting(false);
    }
  };

  // Archive announcement
  const handleArchive = async (id, title) => {
    if (!window.confirm(`Archive announcement "${title}"?`)) return;

    setSubmitting(true);
    try {
      await announcementService.archive(id);
      setNotification({ type: "success", text: `Announcement "${title}" archived.` });
      await loadAnnouncements();
    } catch (err) {
      console.error("Archive error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to archive announcement." });
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered items
  const filtered = announcements.filter((a) => {
    if (statusFilter !== "ALL" && a.status !== statusFilter) return false;
    if (priorityFilter !== "ALL" && a.priority !== priorityFilter) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchTitle = a.title?.toLowerCase().includes(q);
      const matchContent = a.content?.toLowerCase().includes(q);
      if (!matchTitle && !matchContent) return false;
    }
    return true;
  });

  const getDashboardPath = () => (isHr ? "/hr/dashboard" : "/employee/dashboard");

  return (
    <div className="module-page-wrapper">
      {/* Top Header */}
      <header className="module-header-bar">
        <div className="module-header-container">
          <div className="module-header-left">
            <Link to={getDashboardPath()} className="module-back-btn">
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </Link>
            <div className="module-header-meta">
              <h2>Company Announcements</h2>
              <span>{isHr ? "Company-Wide Broadcast & Notifications (All Active Employees)" : "Official Company Broadcasts & Updates"}</span>
            </div>
          </div>

          <div className="module-header-right">
            {isHr && (
              <button
                className="module-action-btn primary"
                onClick={() => {
                  setForm({ title: "", content: "", priority: "NORMAL" });
                  setShowCreateModal(true);
                }}
              >
                <Plus size={16} />
                <span>Create Announcement</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="module-main-container">
        {notification.text && (
          <div className={`module-alert-banner ${notification.type}`}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {notification.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
              <span>{notification.text}</span>
            </div>
            <button
              onClick={() => setNotification({ type: "", text: "" })}
              style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Filter / Search Bar */}
        <div className="module-filter-bar">
          <input
            type="text"
            className="module-search-input"
            placeholder="Search announcements by title or content..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />

          {isHr && (
            <select
              className="module-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="PUBLISHED">Published</option>
              <option value="DRAFT">Draft</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          )}

          <select
            className="module-select"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="ALL">All Priorities</option>
            <option value="NORMAL">Normal</option>
            <option value="IMPORTANT">Important</option>
            <option value="URGENT">Urgent</option>
          </select>
        </div>

        {/* Announcements List / Table */}
        <div className="module-table-container">
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
              <Loader2 size={24} className="spin-animation" />
              <span>Loading announcements...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="module-empty-box">
              <Megaphone size={40} className="module-empty-icon" />
              <div className="module-empty-title">No announcements found</div>
              <div className="module-empty-desc">
                {searchTerm || statusFilter !== "ALL" || priorityFilter !== "ALL"
                  ? "Try adjusting your search filters to find what you're looking for."
                  : isHr
                  ? "Create and publish your first company-wide announcement to notify all active employees."
                  : "Check back later for company broadcasts from HR."}
              </div>
            </div>
          ) : (
            <table className="module-table">
              <thead>
                <tr>
                  <th>Announcement Title</th>
                  <th style={{ width: "120px" }}>Priority</th>
                  {isHr && <th style={{ width: "120px" }}>Status</th>}
                  {!isHr && <th style={{ width: "110px" }}>Read State</th>}
                  <th style={{ width: "160px" }}>Published Date</th>
                  {isHr && <th style={{ width: "160px" }}>Created Date</th>}
                  <th style={{ width: "180px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const isRead = readAnnouncements.includes(item.id);
                  return (
                    <tr key={item.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: "#0f172a", fontSize: "14px" }}>
                          {item.title}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px", maxWidth: "480px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {item.content}
                        </div>
                      </td>
                      <td>
                        <span className={`module-priority-badge ${item.priority}`}>
                          {item.priority}
                        </span>
                      </td>
                      {isHr && (
                        <td>
                          <span className={`module-status-badge ${item.status}`}>
                            {item.status}
                          </span>
                        </td>
                      )}
                      {!isHr && (
                        <td>
                          <span className={`module-status-badge ${isRead ? "PUBLISHED" : "DRAFT"}`}>
                            {isRead ? "Read" : "Unread"}
                          </span>
                        </td>
                      )}
                      <td style={{ fontSize: "13px", color: "#475569" }}>
                        {item.published_at ? new Date(item.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                      </td>
                      {isHr && (
                        <td style={{ fontSize: "13px", color: "#475569" }}>
                          {item.created_at ? new Date(item.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                        </td>
                      )}
                      <td style={{ textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "6px" }}>
                          <button
                            className="module-action-btn secondary"
                            style={{ padding: "5px 10px", fontSize: "12px" }}
                            onClick={() => handleOpenAnnouncement(item)}
                            title="View Details"
                          >
                            <Eye size={13} /> View
                          </button>

                          {isHr && item.status === "DRAFT" && (
                            <button
                              className="module-action-btn primary"
                              style={{ padding: "5px 10px", fontSize: "12px" }}
                              onClick={() => handlePublish(item.id, item.title)}
                              disabled={submitting}
                              title="Publish Company-Wide"
                            >
                              <Send size={13} /> Publish
                            </button>
                          )}

                          {isHr && item.status === "PUBLISHED" && (
                            <button
                              className="module-action-btn secondary"
                              style={{ padding: "5px 10px", fontSize: "12px", color: "#64748b" }}
                              onClick={() => handleArchive(item.id, item.title)}
                              disabled={submitting}
                              title="Archive Announcement"
                            >
                              <Archive size={13} /> Archive
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {/* CREATE ANNOUNCEMENT MODAL (HR ONLY) */}
      {showCreateModal && isHr && (
        <div className="module-modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="module-modal-dialog modal-announcement" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <Megaphone size={20} color="#047857" />
                  <span>Create Company Announcement</span>
                </h3>
                <p className="module-modal-subtitle">
                  Create a company-wide announcement for all active employees.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowCreateModal(false)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              <div className="module-notice-banner">
                <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
                <div>
                  <strong>Company-Wide Broadcast:</strong> Announcements are company-wide. Upon publishing, all active employees will receive an email and in-app notification.
                </div>
              </div>

              <div className="form-grid">
                <div className="form-section-header">
                  Announcement Information
                </div>

                <div className="form-field">
                  <label>
                    Announcement Title <span className="required-star">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Q4 Performance Review Timeline"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    maxLength={255}
                    required
                  />
                </div>

                <div className="form-field">
                  <label>
                    Priority <span className="required-star">*</span>
                  </label>
                  <select
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })}
                  >
                    <option value="NORMAL">Normal</option>
                    <option value="IMPORTANT">Important</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>

                <div className="form-field form-field-full">
                  <label>
                    Announcement Content <span className="required-star">*</span>
                  </label>
                  <textarea
                    className="textarea-tall"
                    placeholder="Type the announcement details and instructions here..."
                    value={form.content}
                    onChange={(e) => setForm({ ...form, content: e.target.value })}
                    required
                  />
                </div>
              </div>
            </div>

            <div className="module-modal-footer">
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setShowCreateModal(false)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => handleCreate(false)}
                disabled={submitting}
              >
                {submitting ? <Loader2 size={14} className="spin-animation" /> : "Save Draft"}
              </button>
              <button
                type="button"
                className="module-action-btn primary"
                onClick={() => handleCreate(true)}
                disabled={submitting}
              >
                {submitting ? <Loader2 size={14} className="spin-animation" /> : <><Send size={14} /> Publish</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VIEW ANNOUNCEMENT DETAILS MODAL */}
      {selectedAnnouncement && (
        <div className="module-modal-overlay" onClick={() => setSelectedAnnouncement(null)}>
          <div className="module-modal-dialog modal-announcement" onClick={(e) => e.stopPropagation()}>
            <div className="module-modal-header">
              <div className="module-modal-header-text">
                <h3 className="module-modal-title">
                  <Megaphone size={20} color="#047857" />
                  <span>{selectedAnnouncement.title}</span>
                </h3>
                <p className="module-modal-subtitle">
                  Official company broadcast details
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedAnnouncement(null)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="module-modal-body">
              <div className="info-grid">
                <div className="info-cell">
                  <span className="info-cell-label">Priority</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedAnnouncement.priority.toLowerCase()}`}>
                      {selectedAnnouncement.priority} Priority
                    </span>
                  </div>
                </div>

                <div className="info-cell">
                  <span className="info-cell-label">Status</span>
                  <div className="info-cell-value">
                    <span className={`badge badge-${selectedAnnouncement.status.toLowerCase()}`}>
                      {selectedAnnouncement.status}
                    </span>
                  </div>
                </div>

                <div className="info-cell" style={{ gridColumn: "1 / -1" }}>
                  <span className="info-cell-label">Published Timestamp</span>
                  <div className="info-cell-value" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <Calendar size={14} color="#64748b" />
                    <span>{selectedAnnouncement.published_at ? new Date(selectedAnnouncement.published_at).toLocaleString() : "Not published yet (Draft)"}</span>
                  </div>
                </div>
              </div>

              <div className="form-section-header">
                Announcement Message
              </div>

              <div className="detail-content-box">
                {selectedAnnouncement.content}
              </div>
            </div>

            <div className="module-modal-footer">
              {isHr && selectedAnnouncement.status === "DRAFT" && (
                <button
                  type="button"
                  className="module-action-btn primary"
                  onClick={() => {
                    const id = selectedAnnouncement.id;
                    const title = selectedAnnouncement.title;
                    setSelectedAnnouncement(null);
                    handlePublish(id, title);
                  }}
                >
                  <Send size={14} /> Publish Announcement
                </button>
              )}
              <button
                type="button"
                className="module-action-btn secondary"
                onClick={() => setSelectedAnnouncement(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
