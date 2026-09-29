import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { 
  Mail, 
  ArrowRight, 
  ArrowLeft, 
  ShieldCheck, 
  RotateCw, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  Lock
} from "lucide-react";
import { authService } from "../services/api";
import { getSession } from "../App";
import "../styles/Login.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  // If already authenticated, redirect to role dashboard
  useEffect(() => {
    const session = getSession();
    if (session && session.token && session.user) {
      const role = String(session.user?.role || "").toLowerCase();
      navigate(role === "hr" ? "/hr/dashboard" : "/employee/dashboard", { replace: true });
    }
  }, [navigate]);

  // Step state: 1 = Email Input, 2 = OTP Input, 3 = Success
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [otpValues, setOtpValues] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  const otpInputRefs = useRef([]);

  // Check if email was pre-passed from another route
  useEffect(() => {
    const passedEmail = location.state?.email || localStorage.getItem("auth_email");
    if (passedEmail) {
      setEmail(passedEmail);
    }
  }, [location]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Focus first OTP field when entering Step 2
  useEffect(() => {
    if (step === 2 && otpInputRefs.current[0]) {
      setTimeout(() => {
        otpInputRefs.current[0]?.focus();
      }, 100);
    }
  }, [step]);

  // STATE 1: Send OTP
  const handleSendOtp = async (e) => {
    e?.preventDefault();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanEmail || !cleanEmail.includes("@")) {
      setError("Please enter a valid corporate email address.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await authService.requestLoginOtp(cleanEmail);
      localStorage.setItem("auth_email", cleanEmail);
      setStep(2);
      setResendCooldown(45);
    } catch (err) {
      console.error("Login OTP error:", err);
      const detail = err.response?.data?.detail || err.message;
      if (err.response?.status === 404) {
        setError("Account not found. Please contact HR.");
      } else if (err.response?.status === 403) {
        setError("Your account is currently inactive. Please contact HR.");
      } else if (typeof detail === "string" && detail.length < 120) {
        setError(detail);
      } else {
        setError("Unable to send OTP right now. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Dedicated clipboard paste handler for 6-digit OTP
  const handleOtpPaste = (e) => {
    e.preventDefault();
    const pasteData = e.clipboardData?.getData("text") || "";
    const cleanDigits = pasteData.replace(/\D/g, "").slice(0, 6);
    if (!cleanDigits) return;

    const newArr = [...otpValues];
    for (let i = 0; i < 6; i++) {
      newArr[i] = cleanDigits[i] || "";
    }
    setOtpValues(newArr);

    const focusIdx = Math.min(cleanDigits.length, 5);
    otpInputRefs.current[focusIdx]?.focus();
  };

  // Handle individual OTP input changes with auto-advancing
  const handleOtpChange = (index, value) => {
    const cleanDigits = value.replace(/\D/g, "");

    // If empty (e.g. deletion)
    if (!cleanDigits) {
      const newArr = [...otpValues];
      newArr[index] = "";
      setOtpValues(newArr);
      return;
    }

    // If multiple digits (pasted or browser autofilled)
    if (cleanDigits.length > 1) {
      const newArr = [...otpValues];
      for (let i = 0; i < cleanDigits.length && index + i < 6; i++) {
        newArr[index + i] = cleanDigits[i];
      }
      setOtpValues(newArr);
      const nextIdx = Math.min(index + cleanDigits.length, 5);
      otpInputRefs.current[nextIdx]?.focus();
      return;
    }

    // Single digit input: take the last entered numeric digit
    const newArr = [...otpValues];
    newArr[index] = cleanDigits.slice(-1);
    setOtpValues(newArr);

    // Auto advance to next cell
    if (index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === "Backspace") {
      if (!otpValues[index] && index > 0) {
        const newArr = [...otpValues];
        newArr[index - 1] = "";
        setOtpValues(newArr);
        otpInputRefs.current[index - 1]?.focus();
      } else {
        const newArr = [...otpValues];
        newArr[index] = "";
        setOtpValues(newArr);
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      e.preventDefault();
      otpInputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      e.preventDefault();
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  // STATE 2 -> STATE 3/4/5: Verify OTP
  const handleVerifyOtp = async (e) => {
    e?.preventDefault();
    const fullOtp = otpValues.join("").trim();

    if (fullOtp.length < 6) {
      setError("Please input the complete 6-digit verification code.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await authService.verifyOtpCode(email, fullOtp);
      
      // Authoritative role retrieval from backend
      const userObj = data.user;
      const role = String(userObj?.role || "").toLowerCase();

      setStep(3); // Success animation

      setTimeout(() => {
        if (role === "hr") {
          navigate("/hr/dashboard", { replace: true });
        } else {
          navigate("/employee/dashboard", { replace: true });
        }
      }, 700);

    } catch (err) {
      console.error("Verification error:", err);
      const detail = err.response?.data?.detail || err.message;
      if (err.response?.status === 400 || err.response?.status === 401) {
        setError("Invalid or expired verification code. Please check and try again.");
      } else {
        setError(typeof detail === "string" ? detail : "Authentication failed. Please verify your OTP code.");
      }
      setLoading(false);
    }
  };

  // Resend OTP
  const handleResend = async () => {
    if (resendCooldown > 0 || loading) return;
    setLoading(true);
    setError("");
    setResendSuccess(false);

    try {
      await authService.resendLoginOtp(email);
      setResendSuccess(true);
      setResendCooldown(45);
      setTimeout(() => setResendSuccess(false), 4000);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(typeof detail === "string" ? detail : "Failed to resend code. Please try again shortly.");
    } finally {
      setLoading(false);
    }
  };

  const handleChangeEmail = () => {
    setStep(1);
    setOtpValues(["", "", "", "", "", ""]);
    setError("");
  };

  return (
    <div className="login-screen-wrap">
      <div className="login-card-container">
        
        {/* Brand Header */}
        <div className="login-brand-header">
          <div className="login-logo-box">M</div>
          <div className="login-brand-info">
            <h2>Mediatize HRMS</h2>
            <span>Unified Workforce Gateway</span>
          </div>
        </div>

        {/* Step Indicator */}
        <div className="login-step-tracker">
          <div className={`step-item ${step === 1 ? "active" : "done"}`}>
            <span className="step-num">1</span>
            <span className="step-lbl">Work Email</span>
          </div>
          <div className="step-track-line"></div>
          <div className={`step-item ${step === 2 ? "active" : step === 3 ? "done" : ""}`}>
            <span className="step-num">2</span>
            <span className="step-lbl">OTP Verification</span>
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="login-alert-banner error" role="alert">
            <AlertCircle size={18} className="alert-ico" />
            <div className="alert-txt">{error}</div>
          </div>
        )}

        {resendSuccess && (
          <div className="login-alert-banner success" role="status">
            <CheckCircle2 size={18} className="alert-ico" />
            <div className="alert-txt">New security verification code sent to your email.</div>
          </div>
        )}

        {/* STEP 1: Enter Email */}
        {step === 1 && (
          <form onSubmit={handleSendOtp} className="login-form-body">
            <div className="login-intro-text">
              <h3>Sign in to Workspace</h3>
              <p>Unified enterprise portal for both HR administration and employee self-service.</p>
            </div>

            <div className="login-field-box">
              <label htmlFor="login-email">Corporate Email Address</label>
              <div className="login-input-shell">
                <Mail size={18} className="login-field-icon" />
                <input
                  id="login-email"
                  type="email"
                  placeholder="name@mediatize.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                  autoFocus
                />
              </div>
              <small className="field-hint">A one-time passcode will be sent to this email</small>
            </div>

            <button 
              type="submit" 
              className="login-primary-btn" 
              disabled={loading}
              id="btn-login-send-otp"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Dispatching Code...</span>
                </>
              ) : (
                <>
                  <span>Continue / Send OTP</span>
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>
        )}

        {/* STEP 2: Enter OTP */}
        {step === 2 && (
          <form onSubmit={handleVerifyOtp} className="login-form-body">
            <div className="login-intro-text">
              <h3>Security Verification</h3>
              <p>
                We sent a 6-digit verification code to: <br />
                <strong className="target-email">{email}</strong>
              </p>
            </div>

            <div className="login-field-box">
              <label htmlFor="otp-digit-0">Enter 6-Digit Security Code</label>
              <div className="otp-digit-inputs" onPaste={handleOtpPaste}>
                {otpValues.map((digit, idx) => (
                  <input
                    key={idx}
                    id={`otp-digit-${idx}`}
                    ref={(el) => (otpInputRefs.current[idx] = el)}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                    onPaste={handleOtpPaste}
                    disabled={loading}
                    className="otp-digit-cell"
                    autoFocus={idx === 0}
                    autoComplete={idx === 0 ? "one-time-code" : "off"}
                    aria-label={`Digit ${idx + 1}`}
                  />
                ))}
              </div>
            </div>

            <button 
              type="submit" 
              className="login-primary-btn" 
              disabled={loading || otpValues.join("").length < 6}
              id="btn-login-verify-otp"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Verifying your account...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={18} />
                  <span>Verify OTP & Open Portal</span>
                </>
              )}
            </button>

            <div className="login-otp-secondary-actions">
              <button
                type="button"
                className="action-link-btn"
                onClick={handleResend}
                disabled={resendCooldown > 0 || loading}
              >
                <RotateCw size={14} className={loading ? "spin" : ""} />
                {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Resend OTP"}
              </button>

              <button
                type="button"
                className="action-link-btn muted"
                onClick={handleChangeEmail}
                disabled={loading}
              >
                Change email
              </button>
            </div>
          </form>
        )}

        {/* STEP 3: Success Transition */}
        {step === 3 && (
          <div className="login-success-state">
            <div className="success-icon-badge">
              <CheckCircle2 size={44} />
            </div>
            <h3>Authentication Successful</h3>
            <p>Access granted. Redirecting to your assigned workspace...</p>
            <div className="login-redirect-loader">
              <Loader2 size={24} className="spinner text-emerald" />
            </div>
          </div>
        )}

        {/* Back to Welcome */}
        <div className="login-footer-nav">
          <button 
            type="button" 
            className="login-back-btn" 
            onClick={() => navigate("/welcome")}
          >
            <ArrowLeft size={15} />
            <span>Back to Welcome Page</span>
          </button>
        </div>

      </div>
    </div>
  );
}