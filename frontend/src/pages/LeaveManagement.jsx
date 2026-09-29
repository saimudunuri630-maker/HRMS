import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { 
  CalendarDays, 
  Layers, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  ArrowLeft, 
  X, 
  Loader2,
  Send,
  Briefcase,
  AlertTriangle,
  RotateCcw,
  Menu,
  Calendar,
  Clock,
  UserCheck
} from "lucide-react";
import { leaveService, authService, employeeService } from "../services/api";
import "../styles/LeaveManagement.css";

// The standard leave categories
const STANDARD_LEAVE_CATEGORIES = [
  { code: "ANNUAL", label: "Annual Leave", title: "ANNUAL LEAVE" },
  { code: "CASUAL", label: "Casual Leave", title: "CASUAL LEAVE" },
  { code: "SICK", label: "Sick Leave", title: "SICK LEAVE" },
];

export default function LeaveManagement({ role: propRole, onToggleSidebar }) {
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

  const [activeTab, setActiveTab] = useState(isHr ? "requests" : "my-requests");
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Data states
  const [requests, setRequests] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [balances, setBalances] = useState([]);
  const [employeesList, setEmployeesList] = useState([]);
  const [selectedEmpFilter, setSelectedEmpFilter] = useState("ALL");

  // Modals state
  const [addLeaveModal, setAddLeaveModal] = useState(false);
  const [approveModal, setApproveModal] = useState({ open: false, request: null, remarks: "" });
  const [rejectModal, setRejectModal] = useState({ open: false, request: null, reason: "", error: "" });
  const [revokeModal, setRevokeModal] = useState({ open: false, request: null, remarks: "" });

  // Today's date in YYYY-MM-DD
  const todayStr = new Date().toISOString().split("T")[0];

  // Forms state
  const [addLeaveForm, setAddLeaveForm] = useState({
    employee_id: "",
    employee_code: "",
    employee_name: "",
    reason_category: "ANNUAL",
    start_date: todayStr,
    end_date: todayStr,
    reason: "",
  });

  const [applyForm, setApplyForm] = useState({
    leave_type_id: "",
    start_date: todayStr,
    end_date: todayStr,
    reason: "",
  });

  const [submitting, setSubmitting] = useState(false);

  // Sync auth profile
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

  // Safe helper to extract employee list
  const extractEmployees = (empRes) => {
    if (Array.isArray(empRes)) return empRes;
    if (Array.isArray(empRes?.employees)) return empRes.employees;
    if (Array.isArray(empRes?.items)) return empRes.items;
    return [];
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [reqData, typeData, balData] = await Promise.all([
        leaveService.listRequests().catch(() => ({ requests: [], total: 0 })),
        leaveService.getLeaveTypes().catch(() => []),
        leaveService.getMyBalances().catch(() => []),
      ]);

      setRequests(reqData.requests || []);
      setLeaveTypes(typeData || []);
      setBalances(balData || []);

      if (typeData && typeData.length > 0 && !applyForm.leave_type_id) {
        setApplyForm((prev) => ({ ...prev, leave_type_id: typeData[0].id }));
      }

      // If HR, load employee roster for Add Leave selector
      if (isHr) {
        try {
          const empRes = await employeeService.listEmployees({ limit: 100 });
          const list = extractEmployees(empRes);
          setEmployeesList(list);
          if (list.length > 0 && !addLeaveForm.employee_id) {
            setAddLeaveForm((prev) => ({
              ...prev,
              employee_id: list[0].id,
              employee_code: list[0].employee_code || `EMP${list[0].id}`,
              employee_name: `${list[0].first_name} ${list[0].last_name}`.trim(),
            }));
          }
        } catch (err) {
          console.error("Failed to load employee list:", err);
        }
      }
    } catch (err) {
      console.error("Failed to load leave data:", err);
      setNotification({ type: "error", text: "Failed to load leave records from server." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [isHr]);

  // When HR filters an employee, load that employee's balances for top cards
  useEffect(() => {
    if (isHr && selectedEmpFilter !== "ALL") {
      const empId = parseInt(selectedEmpFilter);
      if (!isNaN(empId)) {
        leaveService.getEmployeeBalances(empId).then((res) => {
          if (Array.isArray(res) && res.length > 0) {
            setBalances(res);
          }
        }).catch((err) => console.error("Failed to load employee balance:", err));
      }
    } else if (isHr && selectedEmpFilter === "ALL") {
      leaveService.getMyBalances().then((res) => {
        if (Array.isArray(res)) setBalances(res);
      }).catch(() => {});
    }
  }, [selectedEmpFilter, isHr]);

  // Calculate inclusive calendar days (e.g. 26-09 to 27-09 = 2 days)
  const calculateDays = (fromStr, toStr) => {
    if (!fromStr || !toStr) return 0;
    const [y1, m1, d1] = fromStr.split("-").map(Number);
    const [y2, m2, d2] = toStr.split("-").map(Number);
    const from = new Date(y1, m1 - 1, d1);
    const to = new Date(y2, m2 - 1, d2);
    if (isNaN(from.getTime()) || isNaN(to.getTime())) return 0;
    if (to < from) return -1; // Invalid date range
    const diffTime = to.getTime() - from.getTime();
    return Math.round(diffTime / (1000 * 60 * 60 * 24)) + 1;
  };

  const addLeaveDays = calculateDays(addLeaveForm.start_date, addLeaveForm.end_date);
  const isDateRangeInvalid = addLeaveDays < 0;

  // Compute standard category cards strictly for Annual, Casual, Sick
  const getCategoryCard = (cat) => {
    const match = balances.find(
      (b) =>
        (b.leave_type_code || "").toUpperCase() === cat.code ||
        (b.leave_type_name || "").toUpperCase().includes(cat.code)
    );
    if (match) {
      return {
        title: cat.title,
        code: match.leave_type_code || cat.code,
        remaining: match.remaining_days,
        allocated: match.total_allocated,
        used: match.used_days,
        pending: match.pending_days,
      };
    }
    return {
      title: cat.title,
      code: cat.code,
      remaining: 0,
      allocated: 0,
      used: 0,
      pending: 0,
    };
  };

  // Check available days for the currently selected category in Add Leave form
  const getAvailableDaysForForm = () => {
    const card = getCategoryCard({ code: addLeaveForm.reason_category, title: "" });
    return card.remaining;
  };

  const availableForSelection = getAvailableDaysForForm();
  const isInsufficientBalance = addLeaveDays > 0 && addLeaveDays > availableForSelection;

  // Handle employee change in Add Leave form
  const handleEmployeeSelect = (empId) => {
    const id = parseInt(empId);
    const found = employeesList.find((e) => e.id === id);
    if (found) {
      setAddLeaveForm((prev) => ({
        ...prev,
        employee_id: found.id,
        employee_code: found.employee_code || `EMP${found.id}`,
        employee_name: `${found.first_name} ${found.last_name}`.trim(),
      }));
      // Fetch this employee's balance to display accurate availability
      leaveService.getEmployeeBalances(found.id).then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setBalances(res);
        }
      }).catch(() => {});
    }
  };

  // Open Add Leave modal with fresh data
  const handleOpenAddLeaveModal = () => {
    if (employeesList.length === 0) {
      employeeService.listEmployees({ limit: 100 }).then((empRes) => {
        const list = extractEmployees(empRes);
        setEmployeesList(list);
        if (list.length > 0) {
          setAddLeaveForm((prev) => ({
            ...prev,
            employee_id: list[0].id,
            employee_code: list[0].employee_code || `EMP${list[0].id}`,
            employee_name: `${list[0].first_name} ${list[0].last_name}`.trim(),
          }));
        }
      }).catch(() => {});
    }
    setAddLeaveModal(true);
  };

  // Handle HR Add Leave submit
  const handleAddLeaveSubmit = async (e) => {
    e.preventDefault();
    if (!addLeaveForm.employee_id) {
      setNotification({ type: "error", text: "Please select an employee." });
      return;
    }
    if (isDateRangeInvalid) {
      setNotification({ type: "error", text: "To Date cannot be earlier than From Date." });
      return;
    }
    if (addLeaveDays <= 0) {
      setNotification({ type: "error", text: "Invalid leave duration." });
      return;
    }
    if (isInsufficientBalance) {
      setNotification({ 
        type: "error", 
        text: `Insufficient ${addLeaveForm.reason_category} balance. Available: ${availableForSelection} day(s), Requested: ${addLeaveDays} day(s).` 
      });
      return;
    }

    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      const categoryLabel = 
        addLeaveForm.reason_category === "ANNUAL" ? "Annual Leave" :
        addLeaveForm.reason_category === "CASUAL" ? "Casual Leave" : "Sick Leave";

      const finalReason = addLeaveForm.reason.trim() 
        ? `${categoryLabel} - ${addLeaveForm.reason.trim()}`
        : categoryLabel;

      await leaveService.applyLeave({
        employee_id: parseInt(addLeaveForm.employee_id),
        employee_code: addLeaveForm.employee_code,
        leave_type_code: addLeaveForm.reason_category,
        start_date: addLeaveForm.start_date,
        end_date: addLeaveForm.end_date,
        reason: finalReason,
      });

      setNotification({ 
        type: "success", 
        text: `Leave request for ${addLeaveForm.employee_name} created successfully (${addLeaveDays} day(s))!` 
      });
      setAddLeaveModal(false);
      setAddLeaveForm((prev) => ({
        ...prev,
        reason_category: "ANNUAL",
        reason: "",
        start_date: todayStr,
        end_date: todayStr,
      }));
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to create leave record." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Employee Apply for Leave
  const handleApplySubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setNotification({ type: "", text: "" });

    try {
      await leaveService.applyLeave({
        leave_type_id: parseInt(applyForm.leave_type_id),
        start_date: applyForm.start_date,
        end_date: applyForm.end_date,
        reason: applyForm.reason.trim(),
      });

      setNotification({ type: "success", text: "Leave application submitted successfully!" });
      setApplyForm({
        leave_type_id: leaveTypes[0]?.id || "",
        start_date: todayStr,
        end_date: todayStr,
        reason: "",
      });
      setActiveTab("my-requests");
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to apply for leave." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle HR Approve confirmation
  const handleApproveSubmit = async (e) => {
    e.preventDefault();
    if (!approveModal.request) return;
    setSubmitting(true);
    try {
      await leaveService.approveRequest(approveModal.request.id, approveModal.remarks.trim());
      setNotification({ type: "success", text: `Leave request for ${approveModal.request.employee_name} approved successfully!` });
      setApproveModal({ open: false, request: null, remarks: "" });
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to approve leave request." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle HR Reject confirmation (Mandatory reason)
  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectModal.request) return;
    if (!rejectModal.reason || !rejectModal.reason.trim()) {
      setRejectModal((prev) => ({ ...prev, error: "Rejection reason is mandatory." }));
      return;
    }

    setSubmitting(true);
    try {
      await leaveService.rejectRequest(rejectModal.request.id, rejectModal.reason.trim());
      setNotification({ type: "success", text: `Leave request rejected and rejection email sent to ${rejectModal.request.employee_name}.` });
      setRejectModal({ open: false, request: null, reason: "", error: "" });
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to reject leave request." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle HR Revoke confirmation
  const handleRevokeSubmit = async (e) => {
    e.preventDefault();
    if (!revokeModal.request) return;
    setSubmitting(true);
    try {
      await leaveService.revokeRequest(revokeModal.request.id, revokeModal.remarks.trim());
      setNotification({ type: "success", text: `Leave request revoked successfully. Balance restored and status set to REVOKED.` });
      setRevokeModal({ open: false, request: null, remarks: "" });
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to revoke leave request." });
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Cancel (Employee)
  const handleCancelRequest = async (id) => {
    if (!window.confirm("Are you sure you want to cancel this pending leave request?")) return;
    try {
      await leaveService.cancelRequest(id);
      setNotification({ type: "success", text: "Leave request cancelled successfully." });
      loadAllData();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Could not cancel request." });
    }
  };

  // Filtered requests list
  const filteredRequests = requests.filter((r) => {
    if (!isHr || selectedEmpFilter === "ALL") return true;
    return r.employee_id === parseInt(selectedEmpFilter);
  });

  return (
    <div className="leave-page-wrapper">
      {/* Top Header */}
      <header className="leave-header-bar">
        <div className="leave-header-container">
          <div className="leave-header-left">
            {onToggleSidebar && (
              <button 
                type="button"
                className="mobile-hamburger-btn" 
                onClick={onToggleSidebar}
                aria-label="Open navigation sidebar"
              >
                <Menu size={20} />
              </button>
            )}
            <Link to={isHr ? "/hr/dashboard" : "/employee/dashboard"} className="leave-back-btn">
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </Link>
            <div className="leave-header-meta">
              <h2>{isHr ? "Leave Administration Deck" : "My Leave Portal"}</h2>
              <span>Enterprise Workforce Absence Management</span>
            </div>
          </div>

          <div className="leave-header-right">
            {isHr && (
              <button 
                type="button"
                id="btn-add-leave"
                className="leave-submit-btn" 
                onClick={handleOpenAddLeaveModal}
              >
                <Plus size={16} /> <span>Add Leave</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="leave-content-container">
        
        {notification.text && (
          <div className={`leave-alert ${notification.type}`}>
            {notification.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span>{notification.text}</span>
            <button 
              type="button"
              style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer" }} 
              onClick={() => setNotification({ type: "", text: "" })}
            >
              <X size={15} />
            </button>
          </div>
        )}

        {/* Tab & Filter Bar */}
        <div className="leave-controls-row">
          <div className="leave-tabs-bar">
            {isHr ? (
              <>
                <button className={`leave-tab-btn ${activeTab === "requests" ? "active" : ""}`} onClick={() => setActiveTab("requests")}>
                  <CalendarDays size={16} /> Leave Requests ({filteredRequests.length})
                </button>
                <button className={`leave-tab-btn ${activeTab === "balances" ? "active" : ""}`} onClick={() => setActiveTab("balances")}>
                  <Briefcase size={16} /> Employee Balances
                </button>
              </>
            ) : (
              <>
                <button className={`leave-tab-btn ${activeTab === "my-requests" ? "active" : ""}`} onClick={() => setActiveTab("my-requests")}>
                  <CalendarDays size={16} /> My Applications ({requests.length})
                </button>
                <button className={`leave-tab-btn ${activeTab === "apply" ? "active" : ""}`} onClick={() => setActiveTab("apply")}>
                  <Send size={16} /> Apply for Leave
                </button>
                <button className={`leave-tab-btn ${activeTab === "my-balances" ? "active" : ""}`} onClick={() => setActiveTab("my-balances")}>
                  <Briefcase size={16} /> My Leave Balances
                </button>
              </>
            )}
          </div>

          {isHr && (
            <div className="leave-filter-box">
              <label>Filter Employee:</label>
              <select 
                value={selectedEmpFilter} 
                onChange={(e) => setSelectedEmpFilter(e.target.value)}
                className="leave-emp-filter-select"
              >
                <option value="ALL">All Active Employees</option>
                {Array.isArray(employeesList) && employeesList.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name} ({emp.employee_code})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Top Balances Overview Cards - DYNAMIC FROM BACKEND */}
        {balances.length === 0 ? (
          <div className="leave-empty-state" style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: "10px", padding: "20px", marginBottom: "20px", textAlign: "center", color: "#64748b" }}>
            <p style={{ margin: 0, fontSize: "14px", fontWeight: "500" }}>No leave balances found.</p>
            <span style={{ fontSize: "12px", color: "#94a3b8" }}>Allocated leave balances will appear here when configured in the backend.</span>
          </div>
        ) : (
          <div className="leave-balance-grid">
            {balances.map((b) => (
              <div key={b.id || b.leave_type_code || b.leave_type_name} className="leave-kpi-card" data-category={b.leave_type_code}>
                <div className="kpi-title">{b.leave_type_name || b.leave_type_code}</div>
                <div className="kpi-num">
                  {b.remaining_days}{" "}
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#64748b" }}>
                    days left
                  </span>
                </div>
                <div className="kpi-meta">
                  <span>Allocated: {b.total_allocated}</span>
                  <span>Used: {b.used_days}</span>
                  <span>Pending: {b.pending_days}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* TAB 1: ALL REQUESTS / MY REQUESTS */}
        {(activeTab === "requests" || activeTab === "my-requests") && (
          <div className="leave-card">
            <div className="leave-card-header">
              <h3>{isHr ? "All Absence & Leave Requests" : "My Absence Requests"}</h3>
              {!isHr && (
                <button className="leave-submit-btn" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={() => setActiveTab("apply")}>
                  <Plus size={14} /> <span>New Application</span>
                </button>
              )}
            </div>

            {loading ? (
              <div style={{ padding: "40px", textAlign: "center" }}>
                <Loader2 size={30} className="spinner text-emerald" />
                <p style={{ marginTop: "10px", color: "#64748b" }}>Loading leave records...</p>
              </div>
            ) : filteredRequests.length > 0 ? (
              <div className="leave-table-container">
                <table className="leave-table">
                  <thead>
                    <tr>
                      {isHr && <th>Employee</th>}
                      <th>Leave Type</th>
                      <th>Dates</th>
                      <th>Days</th>
                      <th>Reason</th>
                      <th>Status</th>
                      <th>Action Details</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRequests.map((r) => (
                      <tr key={r.id}>
                        {isHr && (
                          <td>
                            <strong>{r.employee_name}</strong>
                            <div style={{ fontSize: "11px", color: "#64748b" }}>{r.employee_code}</div>
                          </td>
                        )}
                        <td><strong>{r.leave_type_name}</strong></td>
                        <td>{r.start_date} to {r.end_date}</td>
                        <td><strong>{r.total_days}</strong></td>
                        <td style={{ maxWidth: "220px" }}>{r.reason}</td>
                        <td>
                          <span className={`status-badge ${r.status.toLowerCase()}`}>
                            {r.status}
                          </span>
                        </td>
                        <td style={{ fontSize: "12px", color: "#64748b" }}>
                          {r.action_by_name ? `${r.action_by_name} (${r.action_reason || "No remarks"})` : "—"}
                        </td>
                        <td>
                          {isHr ? (
                            <>
                              {/* PENDING: Approve & Reject */}
                              {r.status === "PENDING" && (
                                <div style={{ display: "flex", gap: "6px" }}>
                                  <button 
                                    className="btn-action-small approve" 
                                    onClick={() => setApproveModal({ open: true, request: r, remarks: "" })}
                                  >
                                    Approve
                                  </button>
                                  <button 
                                    className="btn-action-small reject" 
                                    onClick={() => setRejectModal({ open: true, request: r, reason: "", error: "" })}
                                  >
                                    Reject
                                  </button>
                                </div>
                              )}

                              {/* APPROVED or REJECTED: ONLY Revoke */}
                              {(r.status === "APPROVED" || r.status === "REJECTED") && (
                                <button 
                                  className="btn-action-small revoke" 
                                  onClick={() => setRevokeModal({ open: true, request: r, remarks: "" })}
                                >
                                  Revoke
                                </button>
                              )}

                              {/* REVOKED or CANCELLED: NO actions */}
                              {(r.status === "REVOKED" || r.status === "CANCELLED") && (
                                <span style={{ color: "#94a3b8", fontSize: "12px" }}>—</span>
                              )}
                            </>
                          ) : (
                            <>
                              {r.status === "PENDING" ? (
                                <button className="btn-action-small cancel" onClick={() => handleCancelRequest(r.id)}>
                                  Cancel
                                </button>
                              ) : (
                                <span style={{ color: "#94a3b8", fontSize: "12px" }}>Completed</span>
                              )}
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
                No leave requests found in workspace.
              </div>
            )}
          </div>
        )}

        {/* TAB 2 (EMPLOYEE): APPLY FOR LEAVE */}
        {activeTab === "apply" && !isHr && (
          <div className="leave-card">
            <div className="leave-card-header">
              <h3>Submit Leave Application</h3>
            </div>
            <form onSubmit={handleApplySubmit} className="leave-form-grid">
              <div className="leave-field-group">
                <label>Leave Category</label>
                <select 
                  value={applyForm.leave_type_id} 
                  onChange={(e) => setApplyForm({ ...applyForm, leave_type_id: e.target.value })}
                  required
                >
                  {leaveTypes.map((lt) => (
                    <option key={lt.id} value={lt.id}>
                      {lt.name} ({lt.code}) - {lt.days_per_year} days/yr
                    </option>
                  ))}
                </select>
              </div>

              <div className="leave-field-group">
                <label>Available Remaining Days</label>
                <input 
                  type="text" 
                  disabled 
                  value={
                    balances.find((b) => b.leave_type_id === parseInt(applyForm.leave_type_id))?.remaining_days ?? "Calculating..."
                  } 
                />
              </div>

              <div className="leave-field-group">
                <label>From Date</label>
                <input 
                  type="date" 
                  value={applyForm.start_date} 
                  onChange={(e) => setApplyForm({ ...applyForm, start_date: e.target.value })} 
                  required 
                />
              </div>

              <div className="leave-field-group">
                <label>To Date</label>
                <input 
                  type="date" 
                  value={applyForm.end_date} 
                  onChange={(e) => setApplyForm({ ...applyForm, end_date: e.target.value })} 
                  required 
                />
              </div>

              <div className="leave-field-group form-full">
                <label>Reason for Leave</label>
                <textarea 
                  rows={3} 
                  placeholder="Provide brief details for your absence request..."
                  value={applyForm.reason} 
                  onChange={(e) => setApplyForm({ ...applyForm, reason: e.target.value })} 
                  required 
                />
              </div>

              <div className="form-full" style={{ display: "flex", justifyContent: "flex-end" }}>
                <button type="submit" className="leave-submit-btn" disabled={submitting}>
                  {submitting ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
                  <span>Submit Leave Application</span>
                </button>
              </div>
            </form>
          </div>
        )}

        {/* TAB 3: BALANCES */}
        {(activeTab === "balances" || activeTab === "my-balances") && (
          <div className="leave-card">
            <div className="leave-card-header">
              <h3>{isHr ? "Employee Leave Entitlements" : "My Detailed Leave Entitlement"}</h3>
            </div>
            <div className="leave-table-container">
              <table className="leave-table">
                <thead>
                  <tr>
                    <th>Leave Type</th>
                    <th>Code</th>
                    <th>Year</th>
                    <th>Total Allocated</th>
                    <th>Used Days</th>
                    <th>Pending Days</th>
                    <th>Remaining Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {balances.map((b) => (
                    <tr key={b.id}>
                      <td><strong>{b.leave_type_name}</strong></td>
                      <td><code>{b.leave_type_code}</code></td>
                      <td>{b.year}</td>
                      <td>{b.total_allocated}</td>
                      <td>{b.used_days}</td>
                      <td>{b.pending_days}</td>
                      <td><strong style={{ color: "#047857", fontSize: "15px" }}>{b.remaining_days}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>

      {/* ============================================================
          MODAL 1: ADD LEAVE (HR ONLY)
          Proper professional modal with Employee, Employee ID,
          Leave Type/Reason, From Date, To Date, Days, and Reason textarea.
          ============================================================ */}
      {addLeaveModal && (
        <div className="modal-overlay" onClick={() => setAddLeaveModal(false)}>
          <div className="modal-content add-leave-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#0f172a" }}>
                Add Leave
              </h3>
              <button 
                type="button" 
                onClick={() => setAddLeaveModal(false)}
                className="modal-close-icon-btn"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAddLeaveSubmit}>
              <div className="add-leave-grid">
                {/* Field 1: Employee Name */}
                <div className="leave-field-group">
                  <label>Employee <span style={{ color: "#dc2626" }}>*</span></label>
                  <select
                    value={addLeaveForm.employee_id}
                    onChange={(e) => handleEmployeeSelect(e.target.value)}
                    required
                  >
                    <option value="">Select Employee...</option>
                    {Array.isArray(employeesList) && employeesList.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.first_name} {emp.last_name} ({emp.employee_code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Field 2: Employee ID */}
                <div className="leave-field-group">
                  <label>Employee ID</label>
                  <input
                    type="text"
                    value={addLeaveForm.employee_code}
                    readOnly
                    placeholder="e.g. EMP001"
                    style={{ background: "#f8fafc", cursor: "not-allowed", color: "#475569" }}
                  />
                </div>

                {/* Field 3: Leave Type / Reason */}
                <div className="leave-field-group form-full">
                  <label>Leave Type / Reason <span style={{ color: "#dc2626" }}>*</span></label>
                  <select
                    value={addLeaveForm.reason_category}
                    onChange={(e) => setAddLeaveForm({ ...addLeaveForm, reason_category: e.target.value })}
                    required
                  >
                    <option value="ANNUAL">Annual Leave</option>
                    <option value="CASUAL">Casual Leave</option>
                    <option value="SICK">Sick Leave</option>
                  </select>
                  <div style={{ fontSize: "12px", color: isInsufficientBalance ? "#dc2626" : "#047857", marginTop: "2px" }}>
                    Available {addLeaveForm.reason_category === "ANNUAL" ? "Annual" : addLeaveForm.reason_category === "CASUAL" ? "Casual" : "Sick"} balance: <strong>{availableForSelection} days</strong>
                  </div>
                </div>

                {/* Field 4: From Date */}
                <div className="leave-field-group">
                  <label>From Date <span style={{ color: "#dc2626" }}>*</span></label>
                  <input
                    type="date"
                    value={addLeaveForm.start_date}
                    onChange={(e) => setAddLeaveForm({ ...addLeaveForm, start_date: e.target.value })}
                    required
                  />
                </div>

                {/* Field 5: To Date */}
                <div className="leave-field-group">
                  <label>To Date <span style={{ color: "#dc2626" }}>*</span></label>
                  <input
                    type="date"
                    value={addLeaveForm.end_date}
                    onChange={(e) => setAddLeaveForm({ ...addLeaveForm, end_date: e.target.value })}
                    required
                  />
                </div>

                {/* Field 6: Days (Auto calculated) */}
                <div className="leave-field-group form-full">
                  <label>Days</label>
                  <input
                    type="text"
                    readOnly
                    value={
                      isDateRangeInvalid 
                        ? "Invalid date range: To Date must be on or after From Date" 
                        : `${addLeaveDays} ${addLeaveDays === 1 ? "day" : "days"}`
                    }
                    style={{
                      background: "#f8fafc",
                      fontWeight: "700",
                      color: isDateRangeInvalid ? "#dc2626" : "#047857",
                      cursor: "not-allowed",
                    }}
                  />
                  {isDateRangeInvalid && (
                    <span style={{ color: "#dc2626", fontSize: "12px", marginTop: "2px" }}>
                      To Date cannot be earlier than From Date.
                    </span>
                  )}
                  {isInsufficientBalance && !isDateRangeInvalid && (
                    <span style={{ color: "#dc2626", fontSize: "12px", marginTop: "2px" }}>
                      Requested days ({addLeaveDays}) exceeds available balance ({availableForSelection}).
                    </span>
                  )}
                </div>

                {/* Field 7: Reason Textarea */}
                <div className="leave-field-group form-full">
                  <label>Reason <span style={{ color: "#dc2626" }}>*</span></label>
                  <textarea
                    rows={3}
                    placeholder="Enter reason for leave (e.g. Family vacation, medical appointment, urgent personal work)..."
                    value={addLeaveForm.reason}
                    onChange={(e) => setAddLeaveForm({ ...addLeaveForm, reason: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-action-small cancel"
                  onClick={() => setAddLeaveModal(false)}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="leave-submit-btn"
                  disabled={submitting || !addLeaveForm.employee_id || isDateRangeInvalid || addLeaveDays <= 0}
                >
                  {submitting ? <Loader2 size={16} className="spinner" /> : null}
                  <span>Create Leave</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================
          MODAL 2: APPROVE LEAVE REQUEST (HR)
          ============================================================ */}
      {approveModal.open && approveModal.request && (
        <div className="modal-overlay" onClick={() => setApproveModal({ open: false, request: null, remarks: "" })}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#047857" }}>
                Approve Leave Request
              </h3>
              <button 
                type="button" 
                onClick={() => setApproveModal({ open: false, request: null, remarks: "" })}
                className="modal-close-icon-btn"
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px", fontSize: "13.5px" }}>
              <div style={{ marginBottom: "6px" }}>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Employee: </span>
                <strong style={{ color: "#0f172a" }}>{approveModal.request.employee_name}</strong>
                <span style={{ color: "#64748b", fontSize: "12px", marginLeft: "6px" }}>({approveModal.request.employee_code})</span>
              </div>
              <div style={{ marginBottom: "6px" }}>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Leave Type: </span>
                <strong style={{ color: "#0f172a" }}>{approveModal.request.leave_type_name}</strong>
              </div>
              <div>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Dates: </span>
                <span style={{ color: "#0f172a" }}>{approveModal.request.start_date} → {approveModal.request.end_date}</span>
                <span style={{ color: "#64748b", marginLeft: "6px" }}>({approveModal.request.total_days} {approveModal.request.total_days === 1 ? "day" : "days"})</span>
              </div>
            </div>

            <form onSubmit={handleApproveSubmit}>
              <div className="leave-field-group">
                <label>Remarks / Notes (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Add any optional approval remarks..."
                  value={approveModal.remarks}
                  onChange={(e) => setApproveModal({ ...approveModal, remarks: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-action-small cancel"
                  onClick={() => setApproveModal({ open: false, request: null, remarks: "" })}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="leave-submit-btn"
                  disabled={submitting}
                >
                  {submitting ? <Loader2 size={16} className="spinner" /> : null}
                  <span>Confirm Approval</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================
          MODAL 3: REJECT LEAVE REQUEST (HR)
          Mandatory rejection reason.
          ============================================================ */}
      {rejectModal.open && rejectModal.request && (
        <div className="modal-overlay" onClick={() => setRejectModal({ open: false, request: null, reason: "", error: "" })}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#991b1b" }}>
                Reject Leave Request
              </h3>
              <button 
                type="button" 
                onClick={() => setRejectModal({ open: false, request: null, reason: "", error: "" })}
                className="modal-close-icon-btn"
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px", fontSize: "13.5px" }}>
              <div style={{ marginBottom: "6px" }}>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Employee: </span>
                <strong style={{ color: "#0f172a" }}>{rejectModal.request.employee_name}</strong>
                <span style={{ color: "#64748b", fontSize: "12px", marginLeft: "6px" }}>({rejectModal.request.employee_code})</span>
              </div>
              <div style={{ marginBottom: "6px" }}>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Leave Type: </span>
                <strong style={{ color: "#0f172a" }}>{rejectModal.request.leave_type_name}</strong>
              </div>
              <div>
                <span style={{ color: "#64748b", fontWeight: "600" }}>Dates: </span>
                <span style={{ color: "#0f172a" }}>{rejectModal.request.start_date} → {rejectModal.request.end_date}</span>
                <span style={{ color: "#64748b", marginLeft: "6px" }}>({rejectModal.request.total_days} {rejectModal.request.total_days === 1 ? "day" : "days"})</span>
              </div>
            </div>

            <form onSubmit={handleRejectSubmit}>
              <div className="leave-field-group">
                <label style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Rejection Reason <span style={{ color: "#dc2626" }}>*</span></span>
                  {rejectModal.error && <span style={{ color: "#dc2626", fontSize: "12px" }}>{rejectModal.error}</span>}
                </label>
                <textarea
                  rows={4}
                  placeholder="Please specify why this leave request is being rejected..."
                  value={rejectModal.reason}
                  onChange={(e) => setRejectModal({ ...rejectModal, reason: e.target.value, error: "" })}
                  required
                  style={{ borderColor: rejectModal.error ? "#dc2626" : undefined }}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-action-small cancel"
                  onClick={() => setRejectModal({ open: false, request: null, reason: "", error: "" })}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="leave-submit-btn"
                  style={{ background: "#dc2626" }}
                  disabled={submitting}
                >
                  {submitting ? <Loader2 size={16} className="spinner" /> : null}
                  <span>Reject Leave</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================
          MODAL 4: REVOKE LEAVE REQUEST (HR)
          ============================================================ */}
      {revokeModal.open && revokeModal.request && (
        <div className="modal-overlay" onClick={() => setRevokeModal({ open: false, request: null, remarks: "" })}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#b45309" }}>
                Revoke Leave Request
              </h3>
              <button 
                type="button" 
                onClick={() => setRevokeModal({ open: false, request: null, remarks: "" })}
                className="modal-close-icon-btn"
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ background: "#fffbeb", padding: "14px 16px", borderRadius: "8px", border: "1px solid #fde68a", marginBottom: "16px", fontSize: "13px", color: "#92400e" }}>
              <p style={{ margin: "0 0 6px 0", fontWeight: "700", display: "flex", alignItems: "center", gap: "6px" }}>
                <AlertTriangle size={16} /> Revoke Confirmation
              </p>
              <p style={{ margin: 0, lineHeight: 1.4 }}>
                {revokeModal.request.status === "APPROVED" 
                  ? `Revoking this approved leave will restore the consumed ${revokeModal.request.total_days} day(s) back to the employee's available balance. Status will become REVOKED and locked from any further actions.`
                  : `Revoking this rejected leave will move status to REVOKED and lock it from further actions. Leave balance is unchanged.`}
              </p>
            </div>

            <div style={{ background: "#f8fafc", padding: "12px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px", fontSize: "13px" }}>
              <div style={{ marginBottom: "4px" }}><strong>Employee:</strong> {revokeModal.request.employee_name} ({revokeModal.request.employee_code})</div>
              <div style={{ marginBottom: "4px" }}><strong>Leave Type:</strong> {revokeModal.request.leave_type_name}</div>
              <div style={{ marginBottom: "4px" }}><strong>Dates:</strong> {revokeModal.request.start_date} to {revokeModal.request.end_date} ({revokeModal.request.total_days} days)</div>
              <div><strong>Current Status:</strong> <span className={`status-badge ${revokeModal.request.status.toLowerCase()}`}>{revokeModal.request.status}</span></div>
            </div>

            <form onSubmit={handleRevokeSubmit}>
              <div className="leave-field-group">
                <label>Revocation Remarks (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Explain why this decision is being revoked..."
                  value={revokeModal.remarks}
                  onChange={(e) => setRevokeModal({ ...revokeModal, remarks: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-action-small cancel"
                  onClick={() => setRevokeModal({ open: false, request: null, remarks: "" })}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="leave-submit-btn"
                  style={{ background: "#b45309" }}
                  disabled={submitting}
                >
                  {submitting ? <Loader2 size={16} className="spinner" /> : null}
                  <span>Confirm Revoke</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
