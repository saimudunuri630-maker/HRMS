import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  CalendarCheck,
  Clock,
  LogIn,
  LogOut,
  Calendar,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  X,
  Loader2,
  Users,
  UserCheck,
  UserX,
  CalendarDays,
  Search,
  RefreshCw
} from "lucide-react";
import { attendanceService, authService } from "../services/api";
import "../styles/Modules.css";

export default function Attendance({ role: propRole }) {
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

  const todayStr = new Date().toISOString().split("T")[0];

  // State
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [notification, setNotification] = useState({ type: "", text: "" });

  // Today's attendance for the logged-in user
  const [myTodayAttendance, setMyTodayAttendance] = useState(null);

  // My attendance history
  const [myHistory, setMyHistory] = useState([]);
  const [historyStatusFilter, setHistoryStatusFilter] = useState("ALL");
  const [historyMonthFilter, setHistoryMonthFilter] = useState(todayStr.slice(0, 7)); // YYYY-MM

  // HR Daily Summary & HR Attendance List
  const [hrSummary, setHrSummary] = useState({
    date: todayStr,
    total_active_employees: 0,
    present: 0,
    absent: 0,
    half_day: 0,
    on_leave: 0,
  });
  const [hrDateFilter, setHrDateFilter] = useState(todayStr);
  const [hrStatusFilter, setHrStatusFilter] = useState("ALL");
  const [hrSearch, setHrSearch] = useState("");
  const [hrAttendanceList, setHrAttendanceList] = useState([]);

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

  // Fetch Attendance Data
  const loadAttendanceData = async () => {
    setLoading(true);
    try {
      // 1. Fetch own today attendance
      const todayRecord = await attendanceService.getTodayAttendance().catch(() => null);
      setMyTodayAttendance(todayRecord);

      // 2. Fetch own history
      const historyRecords = await attendanceService.getMyAttendanceHistory().catch(() => []);
      setMyHistory(Array.isArray(historyRecords) ? historyRecords : (historyRecords?.attendance || historyRecords?.items || []));

      // 3. If HR, fetch summary and attendance list for the selected date
      if (isHr) {
        const [sum, list] = await Promise.all([
          attendanceService.getHrDailySummary(hrDateFilter).catch(() => null),
          attendanceService.getHrAttendanceList({ date: hrDateFilter }).catch(() => []),
        ]);

        if (sum) setHrSummary(sum);
        setHrAttendanceList(Array.isArray(list) ? list : (list?.attendance || list?.items || []));
      }
    } catch (err) {
      console.error("Attendance data fetch error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to load attendance records." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAttendanceData();
  }, [isHr, hrDateFilter]);

  // Handle Login
  const handleCheckIn = async () => {
    setActionLoading(true);
    setNotification({ type: "", text: "" });

    try {
      const res = await attendanceService.checkIn("Logged via HRMS portal");
      setNotification({
        type: "success",
        text: `Logged in successfully at ${formatTime(res.check_in)}! Have a productive day.`,
      });
      await loadAttendanceData();
    } catch (err) {
      console.error("Login error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to login." });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Logout
  const handleCheckOut = async () => {
    setActionLoading(true);
    setNotification({ type: "", text: "" });

    try {
      const res = await attendanceService.checkOut("Completed daily shift");
      setNotification({
        type: "success",
        text: `Logged out successfully! Total working hours: ${res.working_hours || "recorded"}.`,
      });
      await loadAttendanceData();
    } catch (err) {
      console.error("Logout error:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({ type: "error", text: typeof detail === "string" ? detail : "Failed to logout." });
    } finally {
      setActionLoading(false);
    }
  };

  const formatTime = (isoString) => {
    if (!isoString) return "—";
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  // Filter My History
  const filteredMyHistory = myHistory.filter((item) => {
    if (historyStatusFilter !== "ALL" && item.status !== historyStatusFilter) return false;
    if (historyMonthFilter && !item.attendance_date.startsWith(historyMonthFilter)) return false;
    return true;
  });

  // Filter HR Attendance List
  const filteredHrList = hrAttendanceList.filter((item) => {
    if (hrStatusFilter !== "ALL" && item.status !== hrStatusFilter) return false;
    if (hrSearch) {
      const q = hrSearch.toLowerCase();
      const matchName = item.employee_name?.toLowerCase().includes(q);
      const matchCode = item.employee_code?.toLowerCase().includes(q);
      const matchDept = item.department?.toLowerCase().includes(q);
      if (!matchName && !matchCode && !matchDept) return false;
    }
    return true;
  });

  const getDashboardPath = () => (isHr ? "/hr/dashboard" : "/employee/dashboard");

  return (
    <div className="module-page-wrapper">
      {/* Header */}
      <header className="module-header-bar">
        <div className="module-header-container">
          <div className="module-header-left">
            <Link to={getDashboardPath()} className="module-back-btn">
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </Link>
            <div className="module-header-meta">
              <h2>{isHr ? "Workforce Attendance Deck" : "My Attendance & Shift Portal"}</h2>
              <span>{isHr ? "Company-wide daily attendance telemetry and verification" : "Real-time daily punch-in, shift tracking, and history"}</span>
            </div>
          </div>

          <div className="module-header-right">
            <button
              className="btn-secondary"
              onClick={loadAttendanceData}
              disabled={loading}
              title="Refresh attendance"
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
            </button>
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

        {/* HR KPI METRIC SUMMARY CARDS (DYNAMIC - FROM DATABASE) */}
        {isHr && (
          <div style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ fontWeight: 700, fontSize: "16px", color: "#0f172a" }}>
                Workforce Attendance Summary ({hrDateFilter === todayStr ? "Today" : hrDateFilter})
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Summary Date:</span>
                <input
                  type="date"
                  className="module-select"
                  style={{ padding: "6px 10px" }}
                  value={hrDateFilter}
                  onChange={(e) => setHrDateFilter(e.target.value)}
                />
              </div>
            </div>

            <div className="module-kpi-grid">
              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <Users size={16} color="#2563eb" /> Total Active Staff
                </div>
                <div className="module-kpi-value">{hrSummary.total_active_employees}</div>
                <div className="module-kpi-sub">Verified in workforce database</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <UserCheck size={16} color="#16a34a" /> Present
                </div>
                <div className="module-kpi-value" style={{ color: "#16a34a" }}>{hrSummary.present}</div>
                <div className="module-kpi-sub">Punched in & actively working</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <UserX size={16} color="#dc2626" /> Absent
                </div>
                <div className="module-kpi-value" style={{ color: "#dc2626" }}>{hrSummary.absent}</div>
                <div className="module-kpi-sub">No attendance logged today</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <Clock size={16} color="#d97706" /> Half Day
                </div>
                <div className="module-kpi-value" style={{ color: "#d97706" }}>{hrSummary.half_day}</div>
                <div className="module-kpi-sub">Partial hours logged</div>
              </div>

              <div className="module-kpi-card">
                <div className="module-kpi-title">
                  <CalendarDays size={16} color="#7c3aed" /> On Leave
                </div>
                <div className="module-kpi-value" style={{ color: "#7c3aed" }}>{hrSummary.on_leave}</div>
                <div className="module-kpi-sub">Approved leave schedule</div>
              </div>
            </div>
          </div>
        )}

        {/* TODAY'S ATTENDANCE ACTION CARD (BOTH HR & EMPLOYEES) */}
        <div style={{ background: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0", padding: "20px", marginBottom: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <div style={{ fontSize: "12px", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em", color: "#64748b" }}>
                My Daily Attendance & Shift
              </div>
              <div style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a" }}>
                Today: {new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", year: "numeric" })}
              </div>
            </div>

            {/* Login / Logout Buttons */}
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              {!myTodayAttendance?.check_in ? (
                <button
                  className="module-action-btn primary"
                  onClick={handleCheckIn}
                  disabled={actionLoading}
                  style={{ background: "#16a34a", borderColor: "#16a34a" }}
                >
                  {actionLoading ? <Loader2 size={16} className="spin-animation" /> : <><LogIn size={16} /> Login</>}
                </button>
              ) : !myTodayAttendance?.check_out ? (
                <button
                  className="module-action-btn primary"
                  onClick={handleCheckOut}
                  disabled={actionLoading}
                  style={{ background: "#dc2626", borderColor: "#dc2626" }}
                >
                  {actionLoading ? <Loader2 size={16} className="spin-animation" /> : <><LogOut size={16} /> Logout</>}
                </button>
              ) : (
                <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "#16a34a", fontWeight: 700, fontSize: "14px" }}>
                  <CheckCircle2 size={18} /> Shift Finished (Logged Out)
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px", background: "#f8fafc", padding: "16px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Login Time</span>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
                {myTodayAttendance?.check_in ? formatTime(myTodayAttendance.check_in) : "Not Logged In"}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Logout Time</span>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
                {myTodayAttendance?.check_out ? formatTime(myTodayAttendance.check_out) : "Not Logged Out"}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Working Hours</span>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
                {myTodayAttendance?.working_hours || (myTodayAttendance?.check_in && !myTodayAttendance?.check_out ? "In Progress" : "—")}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Shift Status</span>
              <div style={{ marginTop: "4px" }}>
                <span className={`module-status-badge ${myTodayAttendance?.status || "ABSENT"}`}>
                  {myTodayAttendance?.status || "NOT RECORDED"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* HR ATTENDANCE TABLE (ALL EMPLOYEES FOR SELECTED DATE) */}
        {isHr && (
          <div style={{ marginBottom: "32px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ fontWeight: 700, fontSize: "16px", color: "#0f172a" }}>
                All Active Staff Attendance ({filteredHrList.length} Records)
              </div>
            </div>

            <div className="module-filter-bar">
              <input
                type="text"
                className="module-search-input"
                placeholder="Search staff by name, employee code, or department..."
                value={hrSearch}
                onChange={(e) => setHrSearch(e.target.value)}
              />

              <select
                className="module-select"
                value={hrStatusFilter}
                onChange={(e) => setHrStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="PRESENT">Present</option>
                <option value="ABSENT">Absent</option>
                <option value="HALF_DAY">Half Day</option>
                <option value="ON_LEAVE">On Leave</option>
              </select>
            </div>

            <div className="module-table-container">
              {loading ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
                  <Loader2 size={24} className="spin-animation" />
                  <span>Loading workforce attendance...</span>
                </div>
              ) : filteredHrList.length === 0 ? (
                <div className="module-empty-box">
                  <Users size={40} className="module-empty-icon" />
                  <div className="module-empty-title">No attendance records found</div>
                  <div className="module-empty-desc">
                    No active staff match the selected date or search criteria.
                  </div>
                </div>
              ) : (
                <table className="module-table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Department</th>
                      <th style={{ width: "120px" }}>Date</th>
                      <th style={{ width: "120px" }}>Login Time</th>
                      <th style={{ width: "120px" }}>Logout Time</th>
                      <th style={{ width: "130px" }}>Working Hours</th>
                      <th style={{ width: "120px" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHrList.map((item, idx) => (
                      <tr key={item.id || `hr-att-${idx}`}>
                        <td>
                          <div style={{ fontWeight: 600, color: "#0f172a", fontSize: "14px" }}>
                            {item.employee_name || "Employee"}
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748b" }}>
                            {item.employee_code || `ID: ${item.employee_id}`}
                          </div>
                        </td>
                        <td>
                          <span style={{ fontSize: "13px", color: "#475569" }}>
                            {item.department || "General"}
                          </span>
                        </td>
                        <td style={{ fontSize: "13px", color: "#475569" }}>
                          {item.attendance_date}
                        </td>
                        <td style={{ fontSize: "13px", fontWeight: 600, color: item.check_in ? "#16a34a" : "#94a3b8" }}>
                          {formatTime(item.check_in)}
                        </td>
                        <td style={{ fontSize: "13px", fontWeight: 600, color: item.check_out ? "#dc2626" : "#94a3b8" }}>
                          {formatTime(item.check_out)}
                        </td>
                        <td style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                          {item.working_hours || "—"}
                        </td>
                        <td>
                          <span className={`module-status-badge ${item.status}`}>
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* MY ATTENDANCE HISTORY (EMPLOYEES & HR) */}
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
            <div style={{ fontWeight: 700, fontSize: "16px", color: "#0f172a" }}>
              My Attendance History
            </div>
          </div>

          <div className="module-filter-bar">
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>Month:</span>
              <input
                type="month"
                className="module-select"
                value={historyMonthFilter}
                onChange={(e) => setHistoryMonthFilter(e.target.value)}
              />
            </div>

            <select
              className="module-select"
              value={historyStatusFilter}
              onChange={(e) => setHistoryStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="PRESENT">Present</option>
              <option value="HALF_DAY">Half Day</option>
              <option value="ON_LEAVE">On Leave</option>
              <option value="ABSENT">Absent</option>
            </select>
          </div>

          <div className="module-table-container">
            {loading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "48px 0", gap: "10px", color: "#64748b" }}>
                <Loader2 size={24} className="spin-animation" />
                <span>Loading your attendance history...</span>
              </div>
            ) : filteredMyHistory.length === 0 ? (
              <div className="module-empty-box">
                <CalendarCheck size={40} className="module-empty-icon" />
                <div className="module-empty-title">No history records found</div>
                <div className="module-empty-desc">
                  No attendance history matching the selected filters.
                </div>
              </div>
            ) : (
              <table className="module-table">
                <thead>
                  <tr>
                    <th style={{ width: "130px" }}>Date</th>
                    <th style={{ width: "130px" }}>Login Time</th>
                    <th style={{ width: "130px" }}>Logout Time</th>
                    <th style={{ width: "140px" }}>Working Hours</th>
                    <th style={{ width: "130px" }}>Status</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMyHistory.map((h) => (
                    <tr key={h.id}>
                      <td style={{ fontWeight: 600, color: "#0f172a", fontSize: "13px" }}>
                        {h.attendance_date}
                      </td>
                      <td style={{ fontSize: "13px", fontWeight: 600, color: h.check_in ? "#16a34a" : "#94a3b8" }}>
                        {formatTime(h.check_in)}
                      </td>
                      <td style={{ fontSize: "13px", fontWeight: 600, color: h.check_out ? "#dc2626" : "#94a3b8" }}>
                        {formatTime(h.check_out)}
                      </td>
                      <td style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                        {h.working_hours || "—"}
                      </td>
                      <td>
                        <span className={`module-status-badge ${h.status}`}>
                          {h.status}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "#64748b" }}>
                        {h.remarks || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
