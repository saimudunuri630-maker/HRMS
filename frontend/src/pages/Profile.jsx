import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { 
  Mail, 
  Hash, 
  ShieldCheck, 
  Phone, 
  MapPin, 
  Calendar, 
  Camera, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  ArrowLeft, 
  Loader2, 
  Save, 
  Building2, 
  Briefcase,
  FileCheck,
  X,
  Maximize2
} from "lucide-react";
import { profileService } from "../services/api";
import "../styles/Profile.css";

export default function Profile() {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const firstNameInputRef = useRef(null);
  const editSectionRef = useRef(null);

  const [profile, setProfile] = useState(null);
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    address: "",
    date_of_birth: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [photoUploading, setPhotoUploading] = useState(false);
  const [photoViewerOpen, setPhotoViewerOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ type: "", text: "" });

  // Handle ESC key to close photo viewer modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && photoViewerOpen) {
        setPhotoViewerOpen(false);
      }
    };
    if (photoViewerOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [photoViewerOpen]);

  const loadProfile = async () => {
    try {
      const data = await profileService.getMyProfile();
      setProfile(data);
      setFormData({
        first_name: data.first_name || "",
        last_name: data.last_name || "",
        phone: data.phone || "",
        address: data.address || "",
        date_of_birth: data.date_of_birth ? data.date_of_birth.split("T")[0] : "",
      });
    } catch (err) {
      console.error("Profile load failed:", err);
      setStatusMessage({
        type: "error",
        text: "Unable to load corporate profile. Please ensure you are logged in.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("mode") === "edit" || location.hash === "#edit") {
      const timer = setTimeout(() => {
        if (firstNameInputRef.current) {
          firstNameInputRef.current.focus();
          firstNameInputRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 350);
      return () => clearTimeout(timer);
    }
  }, [location, loading]);

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const syncLocalUser = (updatedProfile) => {
    try {
      const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
      let current = {};
      if (stored) {
        try { current = JSON.parse(stored); } catch {}
      }
      const synced = {
        ...current,
        first_name: updatedProfile.first_name,
        last_name: updatedProfile.last_name,
        full_name: `${updatedProfile.first_name || ""} ${updatedProfile.last_name || ""}`.trim() || updatedProfile.full_name,
        profile_photo_url: updatedProfile.profile_photo_url,
        phone: updatedProfile.phone,
        address: updatedProfile.address,
      };
      localStorage.setItem("user", JSON.stringify(synced));
      localStorage.setItem("hrms_user", JSON.stringify(synced));
      window.dispatchEvent(new Event("storage"));
      window.dispatchEvent(new CustomEvent("profileUpdated", { detail: synced }));
    } catch (syncErr) {
      console.warn("Local storage sync error:", syncErr);
    }
  };

  // Profile Information Save
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setStatusMessage({ type: "", text: "" });

    try {
      // Intentionally pass ONLY editable fields to adhere to immutable constraints
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        phone: formData.phone.trim() || null,
        address: formData.address.trim() || null,
        date_of_birth: formData.date_of_birth || null,
      };

      const updated = await profileService.updateMyProfile(payload);
      setProfile(updated);
      syncLocalUser(updated);
      setStatusMessage({
        type: "success",
        text: "Profile updated successfully.",
      });
    } catch (err) {
      console.error("Profile update error:", err);
      const detail = err.response?.data?.detail || err.message;
      setStatusMessage({
        type: "error",
        text: typeof detail === "string" ? detail : "Failed to update profile.",
      });
    } finally {
      setSaving(false);
    }
  };

  // Photo Upload Handler with Desktop & Mobile Camera / File support
  const handlePhotoSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate type: JPEG, PNG, WEBP
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
      setStatusMessage({
        type: "error",
        text: "Invalid file format. Only JPEG, PNG, and WebP images are allowed.",
      });
      return;
    }

    // Validate size: max 5MB
    if (file.size > 5 * 1024 * 1024) {
      setStatusMessage({
        type: "error",
        text: "Photo file exceeds maximum 5MB size limit.",
      });
      return;
    }

    setPhotoUploading(true);
    setStatusMessage({ type: "", text: "" });

    try {
      const updated = await profileService.uploadMyPhoto(file);
      setProfile(updated);
      syncLocalUser(updated);
      setStatusMessage({
        type: "success",
        text: "Profile photo updated successfully.",
      });
    } catch (err) {
      console.error("Photo upload error:", err);
      const detail = err.response?.data?.detail || err.message;
      setStatusMessage({
        type: "error",
        text: typeof detail === "string" ? detail : "Failed to upload photo.",
      });
    } finally {
      setPhotoUploading(false);
    }
  };

  const getDashboardPath = () => {
    if (profile?.role?.toLowerCase() === "hr") return "/hr/dashboard";
    return "/employee/dashboard";
  };

  if (loading) {
    return (
      <div className="profile-loading-screen">
        <Loader2 size={32} className="spinner text-emerald" />
        <p>Loading your corporate credentials...</p>
      </div>
    );
  }

  return (
    <div className="profile-page-wrapper">
      {/* Top Header */}
      <header className="profile-header-bar">
        <div className="profile-header-container">
          <div className="profile-header-left">
            <button className="profile-back-btn" onClick={() => navigate(getDashboardPath())}>
              <ArrowLeft size={16} />
              <span>Back to Dashboard</span>
            </button>
            <div className="profile-header-title">
              <h2>Personal Account Settings</h2>
              <span>Corporate Personnel Record</span>
            </div>
          </div>
          <div className="profile-header-status">
            <span className="badge-verified">
              <FileCheck size={14} /> Verified Member
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="profile-content-container">
        
        {/* Status Alerts */}
        {statusMessage.text && (
          <div className={`profile-status-alert ${statusMessage.type}`}>
            {statusMessage.type === "success" ? (
              <CheckCircle2 size={18} className="flex-shrink-0" />
            ) : (
              <AlertCircle size={18} className="flex-shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}

        <div className="profile-two-column-layout">
          
          {/* ================= LEFT COLUMN: PREVIEW CARD ================= */}
          <section className="profile-preview-card">
            
            {/* Avatar & Photo Upload Trigger */}
            <div className="profile-avatar-container">
              <div className="profile-avatar-wrapper">
                <div 
                  className="profile-avatar-frame clickable"
                  onClick={() => setPhotoViewerOpen(true)}
                  title="Click to view full photo"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setPhotoViewerOpen(true);
                    }
                  }}
                >
                  {profile?.profile_photo_url ? (
                    <img src={profile.profile_photo_url} alt={profile.full_name} className="profile-avatar-image" />
                  ) : (
                    <div className="profile-avatar-fallback">
                      {(profile?.first_name?.charAt(0) || "U")}{(profile?.last_name?.charAt(0) || "")}
                    </div>
                  )}

                  {photoUploading && (
                    <div className="photo-upload-spinner-overlay">
                      <Loader2 size={24} className="spinner text-white" />
                    </div>
                  )}
                </div>

                <button 
                  type="button" 
                  className="profile-avatar-zoom-badge" 
                  onClick={(e) => {
                    e.stopPropagation();
                    setPhotoViewerOpen(true);
                  }}
                  aria-label="Click to view full photo" 
                  title="Click to view full photo"
                >
                  <Maximize2 size={15} />
                </button>
              </div>

              <input 
                ref={fileInputRef}
                type="file" 
                accept="image/jpeg,image/png,image/webp" 
                capture="user"
                onChange={handlePhotoSelect} 
                style={{ display: "none" }} 
              />

              <button 
                type="button" 
                className="btn-change-photo"
                onClick={() => fileInputRef.current?.click()}
                disabled={photoUploading}
              >
                <Camera size={14} />
                <span>{photoUploading ? "Uploading..." : "Change Photo"}</span>
              </button>
              <small className="photo-specs-hint">Click avatar to view • JPEG, PNG, WEBP max 5MB</small>
            </div>

            {/* Profile Core Names & Role */}
            <div className="profile-preview-identity">
              <h3>{profile?.full_name || `${profile?.first_name} ${profile?.last_name}`}</h3>
              <div className="profile-role-pill">
                <ShieldCheck size={13} />
                <span>{profile?.role?.toUpperCase() === "HR" ? "HR Administrator" : "Employee"}</span>
              </div>
            </div>

            {/* Preview Spec List */}
            <div className="profile-spec-list">
              
              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <Hash size={14} className="spec-icon" />
                  <span>Employee Code</span>
                </div>
                <div className="spec-value-group">
                  <strong>{profile?.employee_code || "—"}</strong>
                </div>
              </div>

              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <Mail size={14} className="spec-icon" />
                  <span>Corporate Email</span>
                </div>
                <div className="spec-value-group">
                  <strong className="text-break">{profile?.email || "—"}</strong>
                </div>
              </div>

              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <Building2 size={14} className="spec-icon" />
                  <span>Department</span>
                </div>
                <div className="spec-value-group">
                  <span>{profile?.department_name || (profile?.department_id ? `Department #${profile.department_id}` : "Not Assigned")}</span>
                </div>
              </div>

              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <Briefcase size={14} className="spec-icon" />
                  <span>Designation</span>
                </div>
                <div className="spec-value-group">
                  <span>{profile?.official_designation || profile?.designation || (profile?.role?.toUpperCase() === "HR" ? "HR Administrator" : "Not Assigned")}</span>
                </div>
              </div>

              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <Calendar size={14} className="spec-icon" />
                  <span>Joined Date</span>
                </div>
                <div className="spec-value-group">
                  <span>{profile?.date_of_joining || profile?.joining_date || "—"}</span>
                </div>
              </div>

              <div className="profile-spec-row">
                <div className="spec-label-group">
                  <ShieldCheck size={14} className="spec-icon" />
                  <span>Account Status</span>
                </div>
                <div className="spec-value-group">
                  <span className="spec-status-active">● {profile?.employment_status || "ACTIVE"}</span>
                </div>
              </div>

            </div>

          </section>

          {/* ================= RIGHT COLUMN: EDIT FORM ================= */}
          <section className="profile-edit-section" ref={editSectionRef} id="edit-section">
            <div className="edit-card-header">
              <h3>Edit Personal Information</h3>
              <p>Update your approved personal contact details. Corporate identification keys remain locked.</p>
            </div>

            <form onSubmit={handleProfileSubmit} className="profile-edit-form">
              
              <div className="form-fields-grid">
                
                <div className="profile-form-group">
                  <label htmlFor="first_name">First Name *</label>
                  <input
                    ref={firstNameInputRef}
                    id="first_name"
                    name="first_name"
                    type="text"
                    value={formData.first_name}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="profile-form-group">
                  <label htmlFor="last_name">Last Name *</label>
                  <input
                    id="last_name"
                    name="last_name"
                    type="text"
                    value={formData.last_name}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="profile-form-group">
                  <label htmlFor="phone">Phone Number</label>
                  <div className="input-with-icon">
                    <Phone size={16} className="input-prefix-icon" />
                    <input
                      id="phone"
                      name="phone"
                      type="tel"
                      placeholder="+1 (555) 000-0000"
                      value={formData.phone}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="profile-form-group">
                  <label htmlFor="date_of_birth">Date of Birth</label>
                  <div className="input-with-icon">
                    <Calendar size={16} className="input-prefix-icon" />
                    <input
                      id="date_of_birth"
                      name="date_of_birth"
                      type="date"
                      value={formData.date_of_birth}
                      onChange={handleChange}
                    />
                  </div>
                </div>

              </div>

              <div className="profile-form-group" style={{ marginTop: "14px" }}>
                <label htmlFor="address">Residential Address</label>
                <div className="input-with-icon">
                  <MapPin size={16} className="input-prefix-icon" />
                  <input
                    id="address"
                    name="address"
                    type="text"
                    placeholder="123 Corporate Way, Suite 400"
                    value={formData.address}
                    onChange={handleChange}
                  />
                </div>
              </div>

              {/* Corporate Information (Read-Only) */}
              <div className="corporate-info-card">
                <div className="corporate-info-header">
                  <div className="corporate-title-wrap">
                    <Lock size={14} className="lock-icon" />
                    <h4>Corporate Information (Read-Only)</h4>
                  </div>
                  <span className="corporate-subtext">Managed exclusively by HR Administration</span>
                </div>
                <div className="corporate-grid">
                  <div className="corporate-item">
                    <span className="corp-label">Employee Number</span>
                    <strong className="corp-value">{profile?.employee_code || "—"}</strong>
                  </div>
                  <div className="corporate-item">
                    <span className="corp-label">Registered Corporate Email</span>
                    <strong className="corp-value text-break">{profile?.email || "—"}</strong>
                  </div>
                </div>
              </div>

              {/* Form Action Controls */}
              <div className="profile-form-actions">
                <button 
                  type="submit" 
                  className="btn-profile-save"
                  disabled={saving}
                  id="btn-save-profile"
                >
                  {saving ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Saving Changes...</span>
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      <span>Save Changes</span>
                    </>
                  )}
                </button>

                <button 
                  type="button" 
                  className="btn-profile-cancel"
                  onClick={loadProfile}
                  disabled={saving}
                >
                  Reset Form
                </button>
              </div>

            </form>
          </section>

        </div>
      </main>

      {/* ================= PHOTO VIEWER LIGHTBOX MODAL ================= */}
      {photoViewerOpen && (
        <div 
          className="profile-photo-modal-overlay" 
          onClick={() => setPhotoViewerOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Profile photo viewer"
        >
          <div 
            className="profile-photo-modal-wrapper" 
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              type="button" 
              className="profile-photo-modal-close"
              onClick={() => setPhotoViewerOpen(false)}
              aria-label="Close photo preview"
              title="Close (Esc)"
            >
              <X size={20} />
            </button>

            <div className="profile-photo-modal-body">
              {profile?.profile_photo_url ? (
                <img 
                  src={profile.profile_photo_url} 
                  alt={profile.full_name || "Profile Photo"} 
                  className="profile-photo-modal-img" 
                />
              ) : (
                <div className="profile-photo-modal-fallback-card">
                  <div className="profile-photo-modal-fallback-avatar">
                    {(profile?.first_name?.charAt(0) || "U")}{(profile?.last_name?.charAt(0) || "")}
                  </div>
                  <p className="profile-photo-modal-fallback-hint">No profile photo uploaded yet</p>
                </div>
              )}
            </div>

            <div className="profile-photo-modal-footer">
              <div className="profile-photo-modal-info">
                <span className="profile-photo-modal-name">{profile?.full_name || "Corporate Profile"}</span>
                <span className="profile-photo-modal-code">{profile?.employee_code || profile?.email || ""}</span>
              </div>
              <div className="profile-photo-modal-actions">
                <button
                  type="button"
                  className="profile-photo-modal-btn-change"
                  onClick={() => {
                    setPhotoViewerOpen(false);
                    fileInputRef.current?.click();
                  }}
                  disabled={photoUploading}
                >
                  <Camera size={14} />
                  <span>Change Photo</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
