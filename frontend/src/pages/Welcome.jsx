import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  ShieldCheck, 
  Users, 
  Layers, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  Sparkles,
  Lock
} from "lucide-react";
import { getSession } from "../App";
import "../styles/Welcome.css";

export default function Welcome() {
  const navigate = useNavigate();

  useEffect(() => {
    const session = getSession();
    if (session && session.token && session.user) {
      const role = String(session.user?.role || "").toLowerCase();
      navigate(role === "hr" ? "/hr/dashboard" : "/employee/dashboard", { replace: true });
    }
  }, [navigate]);

  const handleBegin = () => {
    navigate("/login");
  };

  return (
    <div className="wlc-page-wrapper">
      {/* Top Header Strip */}
      <header className="wlc-navbar">
        <div className="wlc-nav-container">
          <div className="wlc-brand">
            <div className="wlc-brand-badge">M</div>
            <div className="wlc-brand-text">
              <span className="wlc-brand-name">Mediatize</span>
              <span className="wlc-brand-sub">HRMS ENTERPRISE</span>
            </div>
          </div>

          <div className="wlc-nav-actions">
            <button className="wlc-nav-login-btn" onClick={handleBegin}>
              Sign In
            </button>
            <button className="wlc-nav-primary-btn" onClick={handleBegin}>
              Let's Begin <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="wlc-hero-container">
        <div className="wlc-hero-content">
          <div className="wlc-pill-badge">
            <Sparkles size={14} className="wlc-pill-icon" />
            <span>Human Resources Management System</span>
          </div>

          <h1 className="wlc-main-heading">
            Manage people. <br />
            Manage processes. <br />
            <span className="wlc-emerald-text">Build better workplaces.</span>
          </h1>

          <p className="wlc-subtext">
            A unified, role-aware workforce operations platform. Streamline employee directories, 
            instant biometric attendance, sprint allocations, and self-service portals with 
            zero-trust enterprise OTP authentication.
          </p>

          <div className="wlc-cta-row">
            <button className="wlc-hero-cta" onClick={handleBegin} id="btn-welcome-begin">
              <span>Let's Begin</span>
              <ArrowRight size={18} />
            </button>
            <div className="wlc-secure-tag">
              <Lock size={14} />
              <span>Zero-Trust OTP Authentication • Role-Guarded Access</span>
            </div>
          </div>

          {/* Key HR Value Metrics */}
          <div className="wlc-metrics-strip">
            <div className="wlc-metric-item">
              <div className="wlc-metric-val">100%</div>
              <div className="wlc-metric-lbl">Role Separation</div>
            </div>
            <div className="wlc-metric-sep"></div>
            <div className="wlc-metric-item">
              <div className="wlc-metric-val">Instant</div>
              <div className="wlc-metric-lbl">OTP Verification</div>
            </div>
            <div className="wlc-metric-sep"></div>
            <div className="wlc-metric-item">
              <div className="wlc-metric-val">Unified</div>
              <div className="wlc-metric-lbl">HR & Staff Desk</div>
            </div>
          </div>
        </div>

        {/* Hero Visual Card Deck */}
        <div className="wlc-hero-visual">
          <div className="wlc-visual-card-deck">
            <div className="wlc-preview-card top-card">
              <div className="wlc-card-header">
                <div className="wlc-card-avatar">HR</div>
                <div>
                  <div className="wlc-card-user">Workforce Command Deck</div>
                  <div className="wlc-card-sub">Active Enterprise Session</div>
                </div>
                <span className="wlc-live-dot">● Active</span>
              </div>
              <div className="wlc-card-kpi-row">
                <div className="wlc-kpi-chip">
                  <small>Headcount</small>
                  <strong>100% Verified</strong>
                </div>
                <div className="wlc-kpi-chip">
                  <small>Security</small>
                  <strong>OTP-Guarded</strong>
                </div>
              </div>
            </div>

            <div className="wlc-feature-grid">
              <div className="wlc-feature-box">
                <div className="wlc-feat-icon green"><Users size={20} /></div>
                <h3>Personnel Directory</h3>
                <p>Centralized employee lifecycle management with strict immutable corporate identities.</p>
              </div>

              <div className="wlc-feature-box">
                <div className="wlc-feat-icon blue"><Layers size={20} /></div>
                <h3>Project Governance</h3>
                <p>Role allocations and sprint rosters with HR management and staff self-service views.</p>
              </div>

              <div className="wlc-feature-box">
                <div className="wlc-feat-icon emerald"><Clock size={20} /></div>
                <h3>Attendance & Leaves</h3>
                <p>Real-time clock tracking, biometric sync, and instant email dispatch alerts.</p>
              </div>

              <div className="wlc-feature-box">
                <div className="wlc-feat-icon purple"><ShieldCheck size={20} /></div>
                <h3>Protected Roles</h3>
                <p>Strict backend-enforced boundaries ensuring HR and staff isolation.</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="wlc-footer">
        <div className="wlc-footer-content">
          <span>© 2026 Mediatize HRMS Inc. All rights reserved.</span>
          <div className="wlc-footer-links">
            <span className="wlc-footer-pill">Enterprise v2.0</span>
            <span className="wlc-footer-pill">Zero-Trust Secured</span>
          </div>
        </div>
      </footer>
    </div>
  );
}