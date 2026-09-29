import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { 
  Users, 
  Search, 
  Filter, 
  Plus, 
  Eye, 
  Edit, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  ArrowLeft, 
  Mail, 
  Phone, 
  Calendar, 
  Building2, 
  Briefcase, 
  MapPin, 
  Lock, 
  X, 
  Loader2, 
  UserCheck, 
  UserX,
  FileCheck,
  FolderKanban,
  Trash2
} from "lucide-react";
import { employeeService, authService } from "../services/api";
import CreateEmployeeModal from "../components/CreateEmployeeModal";
import "../styles/HrEmployees.css";

export default function HrEmployees() {
  const navigate = useNavigate();

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          name: parsed.full_name || (parsed.first_name ? `${parsed.first_name} ${parsed.last_name || ""}`.trim() : parsed.email?.split("@")[0] || "HR User"),
          email: parsed.email || "",
          role: (parsed.role || "HR").toUpperCase(),
          photo: parsed.profile_photo_url || null,
        };
      }
    } catch {}
    return { name: "HR User", email: "", role: "HR", photo: null };
  });

  const [employees, setEmployees] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [notification, setNotification] = useState({ type: "", message: "" });

  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [viewEmployeeModal, setViewEmployeeModal] = useState(null);
  const [editEmployeeModal, setEditEmployeeModal] = useState(null);
  const [removeModalEmployee, setRemoveModalEmployee] = useState(null);
  const [removeSubmitting, setRemoveSubmitting] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState({
    id: null,
    employee_code: "",
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    department: "",
    designation: "",
    address: "",
  });
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Fetch employees list
  const loadEmployees = async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (statusFilter) params.employment_status = statusFilter;

      const data = await employeeService.listEmployees(params);
      setEmployees(data.employees || []);
      setTotalCount(data.total || 0);
    } catch (err) {
      console.error("Failed to load employees:", err);
      setNotification({
        type: "error",
        message: "Failed to retrieve employee directory from backend.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployees();
    const fetchMe = () => {
      authService.getMe().then((meData) => {
        if (meData) {
          setCurrentUser({
            name: meData.full_name || (meData.first_name ? `${meData.first_name} ${meData.last_name || ""}`.trim() : meData.email.split("@")[0]),
            email: meData.email,
            role: (meData.role || "HR").toUpperCase(),
            photo: meData.profile_photo_url || null,
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
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadEmployees();
  };

  // OPEN EDIT MODAL
  const openEditModal = (emp) => {
    setEditForm({
      id: emp.id,
      employee_code: emp.employee_code,
      email: emp.email || emp.user?.email || "Staff Account",
      first_name: emp.first_name || "",
      last_name: emp.last_name || "",
      phone: emp.phone || "",
      department: emp.department || emp.department_name || "Engineering & Operations",
      designation: emp.designation || emp.official_designation || "",
      address: emp.address || "",
    });
    setEditEmployeeModal(emp);
  };

  // SUBMIT EDIT
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditSubmitting(true);

    try {
      // Pass editable fields including department and designation
      const payload = {
        first_name: editForm.first_name.trim(),
        last_name: editForm.last_name.trim(),
        phone: editForm.phone.trim() || null,
        department: editForm.department?.trim() || null,
        designation: editForm.designation?.trim() || null,
        address: editForm.address.trim() || null,
      };

      await employeeService.updateEmployee(editForm.id, payload);

      setNotification({
        type: "success",
        message: `Employee ${editForm.first_name} ${editForm.last_name} updated successfully.`,
      });

      setEditEmployeeModal(null);
      loadEmployees();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({
        type: "error",
        message: typeof detail === "string" ? detail : "Failed to update employee.",
      });
    } finally {
      setEditSubmitting(false);
    }
  };

  // REMOVE EMPLOYEE HANDLER (Part 10, 11, 12: Safe Archival with Confirmation)
  const handleRemoveConfirm = async () => {
    if (!removeModalEmployee) return;
    setRemoveSubmitting(true);
    try {
      await employeeService.removeEmployee(removeModalEmployee.id);
      setNotification({
        type: "success",
        message: `Employee ${removeModalEmployee.first_name} ${removeModalEmployee.last_name} (${removeModalEmployee.employee_code}) has been removed.`,
      });
      setRemoveModalEmployee(null);
      loadEmployees();
    } catch (err) {
      console.error("Remove employee failed:", err);
      const detail = err.response?.data?.detail || err.message;
      setNotification({
        type: "error",
        message: typeof detail === "string" ? detail : "Failed to remove employee.",
      });
    } finally {
      setRemoveSubmitting(false);
    }
  };

  // ACTIVATE / DEACTIVATE
  const handleToggleStatus = async (emp) => {
    const isCurrentlyActive = emp.employment_status === "ACTIVE";
    const actionText = isCurrentlyActive ? "deactivate" : "activate";

    if (!window.confirm(`Are you sure you want to ${actionText} employee ${emp.first_name} ${emp.last_name}?`)) {
      return;
    }

    try {
      if (isCurrentlyActive) {
        await employeeService.deactivateEmployee(emp.id);
        setNotification({
          type: "success",
          message: `Employee ${emp.first_name} ${emp.last_name} deactivated. User session invalidated.`,
        });
      } else {
        await employeeService.activateEmployee(emp.id);
        setNotification({
          type: "success",
          message: `Employee ${emp.first_name} ${emp.last_name} reactivated.`,
        });
      }
      loadEmployees();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setNotification({
        type: "error",
        message: typeof detail === "string" ? detail : `Failed to ${actionText} employee.`,
      });
    }
  };

  return (
    <div className="dir-page-wrapper">
      {/* Top Header */}
      <header className="dir-header-bar">
        <div className="dir-header-container">
          <div className="dir-header-left">
            <Link to="/hr/dashboard" className="dir-back-btn">
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </Link>
            <div className="dir-header-meta">
              <h2>Employee Directory</h2>
              <span>Enterprise Headcount Roster ({totalCount} Registered)</span>
            </div>
          </div>
          <div className="dir-header-right-group">
            <button 
              className="dir-primary-create-btn" 
              onClick={() => setCreateModalOpen(true)}
              id="btn-open-create-employee"
            >
              <Plus size={16} />
              <span>Create Employee</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="dir-content-container">
        
        {/* Notification Alert */}
        {notification.message && (
          <div className={`dir-alert-banner ${notification.type}`}>
            {notification.type === "success" ? (
              <CheckCircle2 size={18} className="flex-shrink-0" />
            ) : (
              <AlertCircle size={18} className="flex-shrink-0" />
            )}
            <span>{notification.message}</span>
            <button className="alert-dismiss" onClick={() => setNotification({ type: "", message: "" })}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* Search & Filter Toolbar (Inspired by Screenshot 2) */}
        <div className="dir-filter-toolbar">
          <form onSubmit={handleSearchSubmit} className="dir-search-wrap">
            <Search size={16} className="search-ico" />
            <input
              type="text"
              placeholder="Search by employee name, code, or work email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button 
                type="button" 
                className="clear-search-btn"
                onClick={() => { setSearchQuery(""); loadEmployees(); }}
              >
                <X size={14} />
              </button>
            )}
          </form>

          <div className="dir-filter-group">
            <div className="filter-select-wrap">
              <Filter size={14} className="filter-ico" />
              <select 
                value={statusFilter} 
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Employment Statuses</option>
                <option value="ACTIVE">Active Only</option>
                <option value="INACTIVE">Inactive</option>
                <option value="ON_NOTICE">On Notice</option>
                <option value="TERMINATED">Terminated</option>
              </select>
            </div>

            <button type="button" className="btn-refresh-dir" onClick={loadEmployees}>
              Refresh
            </button>
          </div>
        </div>

        {/* Employees Table (Screenshot 2 Inspiration) */}
        <div className="dir-table-container">
          {loading ? (
            <div className="dir-loading-state">
              <Loader2 size={32} className="spinner text-emerald" />
              <p>Loading enterprise directory records...</p>
            </div>
          ) : employees.length > 0 ? (
            <table className="dir-enterprise-table">
              <thead>
                <tr>
                  <th>Employee Profile</th>
                  <th>Employee Code</th>
                  <th>Contact Email</th>
                  <th>Department / Designation</th>
                  <th>Joining Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((emp) => (
                  <tr key={emp.id}>
                    <td>
                      <div className="emp-cell-profile">
                        <div className="emp-table-avatar">
                          {emp.profile_photo_url ? (
                            <img src={emp.profile_photo_url} alt={emp.first_name} />
                          ) : (
                            emp.first_name.charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="emp-table-info">
                          <strong>{emp.first_name} {emp.last_name}</strong>
                          <small>{emp.phone || "No phone listed"}</small>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className="emp-code-pill">{emp.employee_code}</span>
                    </td>

                    <td>
                      <div className="emp-email-text">
                        <Mail size={13} className="text-muted" />
                        <span>{emp.email || emp.user?.email || "—"}</span>
                      </div>
                    </td>

                    <td>
                      <div className="emp-role-cell">
                        <span className="dept-name">
                          {emp.department || emp.department_name || (emp.department_id ? `Dept #${emp.department_id}` : "Engineering & Operations")}
                        </span>
                        <small className="desig-name">
                          {emp.designation || emp.official_designation || (emp.designation_id ? `Level ${emp.designation_id}` : "—")}
                        </small>
                      </div>
                    </td>

                    <td>
                      <span className="date-text">{emp.joining_date || "Active Staff"}</span>
                    </td>

                    <td>
                      <span className={`status-badge-pill ${emp.employment_status.toLowerCase()}`}>
                        {emp.employment_status}
                      </span>
                    </td>

                    <td>
                      <div className="table-actions-row">
                        <button 
                          className="action-icon-btn view" 
                          onClick={() => setViewEmployeeModal(emp)}
                          title="View Employee Profile"
                        >
                          <Eye size={15} />
                        </button>

                        <button 
                          className="action-icon-btn edit" 
                          onClick={() => openEditModal(emp)}
                          title="Edit Personal Information"
                        >
                          <Edit size={15} />
                        </button>

                        <button 
                          className={`action-icon-btn ${emp.employment_status === "ACTIVE" ? "deactivate" : "activate"}`} 
                          onClick={() => handleToggleStatus(emp)}
                          title={emp.employment_status === "ACTIVE" ? "Deactivate Account" : "Activate Account"}
                        >
                          {emp.employment_status === "ACTIVE" ? <UserX size={15} /> : <UserCheck size={15} />}
                        </button>

                        <button 
                          className="action-icon-btn remove" 
                          onClick={() => setRemoveModalEmployee(emp)}
                          title="Remove Employee"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="dir-empty-state">
              <Users size={44} className="text-emerald empty-ico" />
              <h3>No Employees Found</h3>
              <p>No records match your query. You can onboard a new employee using the button below.</p>
              <button 
                className="dir-primary-create-btn" 
                onClick={() => setCreateModalOpen(true)}
                style={{ marginTop: "14px", display: "inline-flex" }}
              >
                <Plus size={16} /> Create Employee
              </button>
            </div>
          )}
        </div>
      </main>

      {/* ================= MODAL 1: CREATE EMPLOYEE (Reusing Single Source of Truth) ================= */}
      <CreateEmployeeModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={(created, payload) => {
          setNotification({
            type: "success",
            message: `Employee account created for ${created.first_name} ${created.last_name} (${created.employee_code}) with designation "${created.designation || payload.designation}". An onboarding welcome email was sent to ${payload.email}!`,
          });
          loadEmployees();
        }}
      />

      {/* ================= MODAL 2: VIEW EMPLOYEE PROFILE (Part 11) ================= */}
      {viewEmployeeModal && (
        <div className="dir-modal-backdrop">
          <div className="dir-modal-card view-card">
            <div className="modal-header">
              <div>
                <h3>Employee Dossier</h3>
                <span className="emp-code-pill">{viewEmployeeModal.employee_code}</span>
              </div>
              <button className="modal-close-btn" onClick={() => setViewEmployeeModal(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="view-modal-content">
              <div className="view-top-profile">
                <div className="view-avatar-box">
                  {viewEmployeeModal.profile_photo_url ? (
                    <img src={viewEmployeeModal.profile_photo_url} alt={viewEmployeeModal.first_name} />
                  ) : (
                    viewEmployeeModal.first_name.charAt(0).toUpperCase()
                  )}
                </div>
                <div className="view-meta-box">
                  <h4>{viewEmployeeModal.first_name} {viewEmployeeModal.last_name}</h4>
                  <p>{viewEmployeeModal.email || viewEmployeeModal.user?.email}</p>
                  <span className={`status-badge-pill ${viewEmployeeModal.employment_status.toLowerCase()}`}>
                    {viewEmployeeModal.employment_status}
                  </span>
                </div>
              </div>

              <div className="view-details-grid">
                <div className="view-detail-item">
                  <span className="detail-lbl">Employee Code</span>
                  <strong>{viewEmployeeModal.employee_code}</strong>
                </div>

                <div className="view-detail-item">
                  <span className="detail-lbl">Contact Phone</span>
                  <strong>{viewEmployeeModal.phone || "Not recorded"}</strong>
                </div>

                <div className="view-detail-item">
                  <span className="detail-lbl">Department</span>
                  <strong>{viewEmployeeModal.department || viewEmployeeModal.department_name || (viewEmployeeModal.department_id ? `Dept #${viewEmployeeModal.department_id}` : "Engineering & Operations")}</strong>
                </div>

                <div className="view-detail-item">
                  <span className="detail-lbl">Designation</span>
                  <strong>{viewEmployeeModal.designation || viewEmployeeModal.official_designation || (viewEmployeeModal.designation_id ? `Level ${viewEmployeeModal.designation_id}` : "—")}</strong>
                </div>

                <div className="view-detail-item">
                  <span className="detail-lbl">Joining Date</span>
                  <strong>{viewEmployeeModal.joining_date || "Active Staff"}</strong>
                </div>

                <div className="view-detail-item">
                  <span className="detail-lbl">Authentication Mode</span>
                  <strong>Zero-Trust OTP</strong>
                </div>
              </div>

              {viewEmployeeModal.address && (
                <div className="view-address-strip">
                  <MapPin size={15} className="text-muted" />
                  <span>{viewEmployeeModal.address}</span>
                </div>
              )}
            </div>

            <div className="modal-footer-actions">
              <button className="btn-modal-cancel" onClick={() => setViewEmployeeModal(null)}>
                Close Dossier
              </button>
              <button 
                className="btn-modal-primary" 
                onClick={() => {
                  const emp = viewEmployeeModal;
                  setViewEmployeeModal(null);
                  openEditModal(emp);
                }}
              >
                <Edit size={15} /> Edit Personnel Data
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL 3: EDIT EMPLOYEE (IMMUTABLE PROTECTED) ================= */}
      {editEmployeeModal && (
        <div className="dir-modal-backdrop">
          <div className="dir-modal-card">
            <div className="modal-header">
              <div>
                <h3>Edit Employee Record</h3>
                <p>Corporate identification keys are locked and immutable.</p>
              </div>
              <button className="modal-close-btn" onClick={() => setEditEmployeeModal(null)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="modal-form-body">
              
              {/* Immutable Indicators */}
              <div className="modal-immutable-banner">
                <div className="immutable-preview-pill">
                  <span>Code:</span>
                  <strong>{editForm.employee_code}</strong>
                  <Lock size={12} className="text-muted" />
                </div>
                <div className="immutable-preview-pill">
                  <span>Email:</span>
                  <strong>{editForm.email}</strong>
                  <Lock size={12} className="text-muted" />
                </div>
              </div>

              <div className="modal-form-grid" style={{ marginTop: "14px" }}>
                <div className="modal-input-field">
                  <label htmlFor="edit_fn">First Name *</label>
                  <input
                    id="edit_fn"
                    type="text"
                    value={editForm.first_name}
                    onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                    required
                  />
                </div>

                <div className="modal-input-field">
                  <label htmlFor="edit_ln">Last Name *</label>
                  <input
                    id="edit_ln"
                    type="text"
                    value={editForm.last_name}
                    onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="modal-form-grid" style={{ marginTop: "12px" }}>
                <div className="modal-input-field">
                  <label htmlFor="edit_phone">Phone Number</label>
                  <input
                    id="edit_phone"
                    type="tel"
                    value={editForm.phone}
                    onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  />
                </div>

                <div className="modal-input-field">
                  <label htmlFor="edit_dept">Department</label>
                  <select
                    id="edit_dept"
                    value={editForm.department || "Engineering & Operations"}
                    onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                  >
                    <option value="Engineering & Operations">Engineering & Operations</option>
                    <option value="Product & Design">Product & Design</option>
                    <option value="Quality Assurance">Quality Assurance</option>
                    <option value="Human Resources">Human Resources</option>
                    <option value="Marketing & Sales">Marketing & Sales</option>
                    <option value="Finance & Accounts">Finance & Accounts</option>
                    <option value="Executive & Management">Executive & Management</option>
                  </select>
                </div>
              </div>

              <div className="modal-input-field" style={{ marginTop: "12px" }}>
                <label htmlFor="edit_desig">Designation</label>
                <input
                  id="edit_desig"
                  type="text"
                  value={editForm.designation}
                  onChange={(e) => setEditForm({ ...editForm, designation: e.target.value })}
                  placeholder="e.g. Backend Developer"
                />
              </div>

              <div className="modal-input-field" style={{ marginTop: "12px" }}>
                <label htmlFor="edit_address">Address</label>
                <input
                  id="edit_address"
                  type="text"
                  value={editForm.address}
                  onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                />
              </div>

              <div className="modal-footer-actions">
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setEditEmployeeModal(null)}
                  disabled={editSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-modal-primary"
                  disabled={editSubmitting}
                >
                  {editSubmitting ? "Saving..." : "Save Modifications"}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL 4: CONFIRM REMOVE EMPLOYEE (Part 10, 11, 12) ================= */}
      {removeModalEmployee && (
        <div className="dir-modal-backdrop">
          <div className="dir-modal-card confirm-remove-card">
            <div className="confirm-remove-body">
              <div className="confirm-remove-icon-wrap">
                <Trash2 size={24} />
              </div>
              <h3 className="confirm-remove-title">Remove Employee?</h3>
              <p className="confirm-remove-desc">
                Are you sure you want to remove:
              </p>

              <div className="confirm-remove-emp-box">
                <div className="confirm-remove-emp-name">
                  {removeModalEmployee.first_name} {removeModalEmployee.last_name}
                </div>
                <div className="confirm-remove-emp-meta">
                  {removeModalEmployee.employee_code} &bull; {removeModalEmployee.designation || removeModalEmployee.official_designation || "Staff Member"} ({removeModalEmployee.department || "Engineering & Operations"})
                </div>
              </div>

              <div className="confirm-remove-warning">
                This employee will no longer be an active employee in Mediatize HRMS. Historical records (such as past project assignments, attendance, work reports) will remain preserved.
              </div>

              <div className="modal-footer-actions" style={{ padding: 0, marginTop: "16px", border: "none" }}>
                <button
                  type="button"
                  className="btn-modal-cancel"
                  onClick={() => setRemoveModalEmployee(null)}
                  disabled={removeSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-modal-danger"
                  onClick={handleRemoveConfirm}
                  disabled={removeSubmitting}
                  id="btn-confirm-remove-employee"
                >
                  {removeSubmitting ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Removing Employee...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 size={15} />
                      <span>Remove Employee</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
