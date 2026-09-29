import React, { useState } from "react";
import { 
  X, 
  Mail, 
  Phone, 
  Calendar, 
  Building2, 
  Briefcase, 
  MapPin, 
  FileCheck, 
  Loader2, 
  AlertCircle,
  Hash
} from "lucide-react";
import { employeeService } from "../services/api";

const INITIAL_FORM = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  employee_code: "",
  department: "Engineering & Operations",
  designation: "",
  date_of_birth: "",
  joining_date: new Date().toISOString().split("T")[0],
  address: "",
};

export default function CreateEmployeeModal({ isOpen, onClose, onSuccess }) {
  const [createForm, setCreateForm] = useState(INITIAL_FORM);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  if (!isOpen) return null;

  const handleModalClose = () => {
    if (createSubmitting) return;
    setErrorMessage("");
    onClose();
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    // Explicit Designation Validation (HR must explicitly provide designation)
    const cleanDesignation = createForm.designation?.trim();
    if (!cleanDesignation) {
      setErrorMessage("Designation is required.");
      return;
    }

    setCreateSubmitting(true);

    try {
      const payload = {
        first_name: createForm.first_name.trim(),
        last_name: createForm.last_name.trim(),
        email: createForm.email.trim().toLowerCase(),
        phone: createForm.phone.trim() || null,
        department: createForm.department?.trim() || "Engineering & Operations",
        designation: cleanDesignation,
        date_of_birth: createForm.date_of_birth || null,
        joining_date: createForm.joining_date || null,
        address: createForm.address.trim() || null,
      };

      if (createForm.employee_code?.trim()) {
        payload.employee_code = createForm.employee_code.trim().toUpperCase();
      }

      const created = await employeeService.createEmployee(payload);

      // Reset form and notify parent
      setCreateForm(INITIAL_FORM);
      setErrorMessage("");
      if (onSuccess) {
        onSuccess(created, payload);
      }
      onClose();
    } catch (err) {
      console.error("Create employee failed:", err);
      const detail = err.response?.data?.detail || err.message;
      setErrorMessage(
        typeof detail === "string" ? detail : "Failed to create employee. Please verify details."
      );
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className="dir-modal-backdrop" onClick={handleModalClose}>
      <div 
        className="dir-modal-card" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-emp-title"
      >
        <div className="modal-header">
          <div>
            <h3 id="create-emp-title">Create New Employee</h3>
            <p>Register a new corporate member. Login credentials and welcome email will be sent.</p>
          </div>
          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={handleModalClose}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleCreateSubmit} className="modal-form-body">
          {errorMessage && (
            <div 
              className="modal-error-alert" 
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#b91c1c",
                padding: "10px 14px",
                borderRadius: "8px",
                marginBottom: "14px",
                fontSize: "13px"
              }}
            >
              <AlertCircle size={16} className="flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="modal-form-grid">
            <div className="modal-input-field">
              <label htmlFor="create_fn">First Name *</label>
              <input
                id="create_fn"
                type="text"
                placeholder="e.g. John"
                value={createForm.first_name}
                onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })}
                required
                autoFocus
              />
            </div>

            <div className="modal-input-field">
              <label htmlFor="create_ln">Last Name *</label>
              <input
                id="create_ln"
                type="text"
                placeholder="e.g. Doe"
                value={createForm.last_name}
                onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="modal-input-field" style={{ marginTop: "12px" }}>
            <label htmlFor="create_email">Corporate Work Email * (Login Identity)</label>
            <div className="modal-input-with-icon">
              <Mail size={16} className="modal-input-icon" />
              <input
                id="create_email"
                type="email"
                placeholder="name@mediatize.com"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                required
              />
            </div>
            <small className="field-help">This email becomes the employee's permanent OTP login identity.</small>
          </div>

          <div className="modal-form-grid" style={{ marginTop: "12px" }}>
            <div className="modal-input-field">
              <label htmlFor="create_phone">Phone Number</label>
              <div className="modal-input-with-icon">
                <Phone size={16} className="modal-input-icon" />
                <input
                  id="create_phone"
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  value={createForm.phone}
                  onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-input-field">
              <label htmlFor="create_code">Employee ID (Optional)</label>
              <div className="modal-input-with-icon">
                <Hash size={16} className="modal-input-icon" />
                <input
                  id="create_code"
                  type="text"
                  placeholder="Auto-generated (e.g. EMP004)"
                  value={createForm.employee_code}
                  onChange={(e) => setCreateForm({ ...createForm, employee_code: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="modal-form-grid" style={{ marginTop: "12px" }}>
            <div className="modal-input-field">
              <label htmlFor="create_dept">Department *</label>
              <div className="modal-input-with-icon">
                <Building2 size={16} className="modal-input-icon" />
                <select
                  id="create_dept"
                  value={createForm.department}
                  onChange={(e) => setCreateForm({ ...createForm, department: e.target.value })}
                  required
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

            <div className="modal-input-field">
              <label htmlFor="create_desig">Designation *</label>
              <div className="modal-input-with-icon">
                <Briefcase size={16} className="modal-input-icon" />
                <input
                  id="create_desig"
                  type="text"
                  placeholder="e.g. Backend Developer"
                  value={createForm.designation}
                  onChange={(e) => setCreateForm({ ...createForm, designation: e.target.value })}
                  required
                />
              </div>
            </div>
          </div>

          <div className="modal-form-grid" style={{ marginTop: "12px" }}>
            <div className="modal-input-field">
              <label htmlFor="create_dob">Date of Birth</label>
              <div className="modal-input-with-icon">
                <Calendar size={16} className="modal-input-icon" />
                <input
                  id="create_dob"
                  type="date"
                  value={createForm.date_of_birth}
                  onChange={(e) => setCreateForm({ ...createForm, date_of_birth: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-input-field">
              <label htmlFor="create_date">Joining Date *</label>
              <div className="modal-input-with-icon">
                <Calendar size={16} className="modal-input-icon" />
                <input
                  id="create_date"
                  type="date"
                  value={createForm.joining_date}
                  onChange={(e) => setCreateForm({ ...createForm, joining_date: e.target.value })}
                  required
                />
              </div>
            </div>
          </div>

          <div className="modal-input-field" style={{ marginTop: "12px" }}>
            <label htmlFor="create_address">Office / Residential Address</label>
            <div className="modal-input-with-icon">
              <MapPin size={16} className="modal-input-icon" />
              <input
                id="create_address"
                type="text"
                placeholder="e.g. Tech Park Tower 4, Bangalore"
                value={createForm.address}
                onChange={(e) => setCreateForm({ ...createForm, address: e.target.value })}
              />
            </div>
          </div>

          {/* Onboarding Notice */}
          <div className="modal-onboarding-alert" style={{ marginTop: "14px" }}>
            <FileCheck size={18} className="text-emerald flex-shrink-0" />
            <p>
              Upon submission, the employee account will be registered.
              The employee will receive an onboarding welcome email and can immediately log in via OTP authentication.
            </p>
          </div>

          <div className="modal-footer-actions">
            <button
              type="button"
              className="btn-modal-cancel"
              onClick={handleModalClose}
              disabled={createSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-modal-primary"
              disabled={createSubmitting}
              id="btn-submit-create-employee"
            >
              {createSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Creating Employee...</span>
                </>
              ) : (
                <span>Create Employee</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
