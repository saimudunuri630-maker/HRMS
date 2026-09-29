import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { User, Edit3, LogOut, ChevronDown, ShieldCheck, Mail } from "lucide-react";
import { authService } from "../services/api";
import "../styles/ProfileDropdown.css";

/**
 * ProfileDropdown Component
 * 
 * Reusable header dropdown supporting:
 * - Direct Profile Navigation (View Profile)
 * - Profile Edit Screen (Edit Profile)
 * - Sign Out (Calls the exact same authService.logout() as the sidebar Sign Out)
 * - Full outside-click & Escape key dismissal
 * - Strict ARIA accessibility compliance
 */
export default function ProfileDropdown({ currentUser = {}, role, employeeCode }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const triggerRef = useRef(null);
  const navigate = useNavigate();

  // Normalize role and profile paths
  const userRole = String(role || currentUser?.role || "employee").toLowerCase();
  const isHr = userRole === "hr";
  const profileBasePath = isHr ? "/hr/profile" : "/employee/profile";
  
  const [userState, setUserState] = useState(currentUser || {});

  useEffect(() => {
    setUserState(currentUser || {});
  }, [currentUser]);

  useEffect(() => {
    const handleProfileSync = (e) => {
      if (e?.detail) {
        setUserState((prev) => ({ ...prev, ...e.detail }));
      } else {
        try {
          const stored = localStorage.getItem("user") || localStorage.getItem("hrms_user");
          if (stored) setUserState(JSON.parse(stored));
        } catch {}
      }
    };
    window.addEventListener("profileUpdated", handleProfileSync);
    window.addEventListener("storage", handleProfileSync);
    return () => {
      window.removeEventListener("profileUpdated", handleProfileSync);
      window.removeEventListener("storage", handleProfileSync);
    };
  }, []);

  const displayName = userState?.name || userState?.full_name || (userState?.first_name ? `${userState.first_name} ${userState.last_name || ""}`.trim() : (isHr ? "HR Manager" : "Employee"));
  const displayEmail = userState?.email || "";
  const displayRoleLabel = isHr ? "HR Administrator" : "Employee";
  const displayBadge = employeeCode || userState?.employee_code || (isHr ? "HR" : "STAFF");
  const photoUrl = userState?.photo || userState?.profile_photo_url || null;

  // Handle outside click & Escape key dismissal
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("touchstart", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const toggleDropdown = () => {
    setIsOpen((prev) => !prev);
  };

  const handleViewProfile = () => {
    setIsOpen(false);
    navigate(profileBasePath);
  };

  const handleEditProfile = () => {
    setIsOpen(false);
    navigate(`${profileBasePath}?mode=edit`);
  };

  const handleSignOut = () => {
    setIsOpen(false);
    // EXACT SAME LOGOUT FUNCTION AS THE BOTTOM-LEFT SIDEBAR SIGN OUT
    authService.logout();
  };

  return (
    <div className="profile-dropdown-container" ref={dropdownRef}>
      {/* Top Header Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        className={`profile-dropdown-trigger ${isOpen ? "active" : ""}`}
        onClick={toggleDropdown}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls="user-profile-menu-panel"
        id="user-profile-trigger-btn"
        title="Account & Profile options"
      >
        <div className={`user-avatar ${isHr ? "hr" : "emp"}`}>
          {photoUrl ? (
            <img src={photoUrl} alt={displayName} className="avatar-img" />
          ) : (
            displayName.charAt(0).toUpperCase()
          )}
        </div>
        <div className="user-text">
          <strong className="user-display-name">{displayName}</strong>
          <small className={isHr ? "user-role-badge" : "user-emp-code"}>{displayBadge}</small>
        </div>
        <ChevronDown size={14} className={`dropdown-chevron ${isOpen ? "rotate" : ""}`} />
      </button>

      {/* Dropdown Popup Menu */}
      {isOpen && (
        <div
          id="user-profile-menu-panel"
          className="profile-dropdown-menu"
          role="menu"
          aria-labelledby="user-profile-trigger-btn"
          aria-orientation="vertical"
        >
          {/* Menu Header with User Details */}
          <div className="dropdown-user-header">
            <div className="header-meta-row">
              <div className={`user-avatar ${isHr ? "hr" : "emp"} lg`}>
                {photoUrl ? (
                  <img src={photoUrl} alt={displayName} className="avatar-img" />
                ) : (
                  displayName.charAt(0).toUpperCase()
                )}
              </div>
              <div className="header-info-details">
                <span className="info-name" title={displayName}>{displayName}</span>
                {displayEmail && (
                  <span className="info-email" title={displayEmail}>
                    <Mail size={11} className="inline-icon" /> {displayEmail}
                  </span>
                )}
                <div className="info-badge-row">
                  <span className={`badge-role-tag ${isHr ? "hr-tag" : "emp-tag"}`}>
                    <ShieldCheck size={10} /> {displayRoleLabel}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="dropdown-divider" />

          {/* Action Links */}
          <div className="dropdown-menu-items">
            <button
              type="button"
              className="dropdown-menu-item"
              role="menuitem"
              onClick={handleViewProfile}
            >
              <User size={16} className="item-icon" />
              <div className="item-text-group">
                <span className="item-title">View Profile</span>
                <span className="item-desc">Access identity & records</span>
              </div>
            </button>

            <button
              type="button"
              className="dropdown-menu-item"
              role="menuitem"
              onClick={handleEditProfile}
            >
              <Edit3 size={16} className="item-icon" />
              <div className="item-text-group">
                <span className="item-title">Edit Profile</span>
                <span className="item-desc">Update contact information</span>
              </div>
            </button>
          </div>

          <div className="dropdown-divider" />

          {/* Sign Out Action Item */}
          <div className="dropdown-footer-actions">
            <button
              type="button"
              className="dropdown-menu-item dropdown-logout-item"
              role="menuitem"
              onClick={handleSignOut}
            >
              <LogOut size={16} className="item-icon logout-icon" />
              <div className="item-text-group">
                <span className="item-title logout-title">Sign Out</span>
                <span className="item-desc logout-desc">Terminate active session</span>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
