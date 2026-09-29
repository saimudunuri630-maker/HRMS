import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, RotateCw, AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { authService } from "../services/api";
import "../styles/Login.css";

export default function VerifyOTP() {
  const [otpValues, setOtpValues] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(45);
  const [email, setEmail] = useState("");

  const otpInputRefs = useRef([]);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const savedEmail = location.state?.email || localStorage.getItem("auth_email");
    if (!savedEmail) {
      navigate("/login", { replace: true });
    } else {
      setEmail(savedEmail);
    }
  }, [location, navigate]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => setResendCooldown((p) => p - 1), 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Focus first cell on mount
  useEffect(() => {
    if (otpInputRefs.current[0]) {
      setTimeout(() => otpInputRefs.current[0]?.focus(), 100);
    }
  }, []);

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

  const handleOtpChange = (index, value) => {
    const cleanDigits = value.replace(/\D/g, "");

    if (!cleanDigits) {
      const newArr = [...otpValues];
      newArr[index] = "";
      setOtpValues(newArr);
      return;
    }

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

    const newArr = [...otpValues];
    newArr[index] = cleanDigits.slice(-1);
    setOtpValues(newArr);

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

  const handleVerify = async (e) => {
    e.preventDefault();
    const cleanOtp = otpValues.join("").trim();

    if (cleanOtp.length < 6) {
      setError("Please input the complete 6-digit verification code.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await authService.verifyOtpCode(email, cleanOtp);
      const user = data.user;
      const role = String(user?.role || "").toLowerCase();

      if (role === "hr") {
        navigate("/hr/dashboard", { replace: true });
      } else {
        navigate("/employee/dashboard", { replace: true });
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(typeof detail === "string" ? detail : "Invalid code. Please verify and retry.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || loading) return;
    setLoading(true);
    setError("");
    try {
      await authService.resendLoginOtp(email);
      setResendCooldown(45);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(typeof detail === "string" ? detail : "Failed to resend code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen-wrap">
      <div className="login-card-container">
        <div className="login-brand-header">
          <div className="login-logo-box">M</div>
          <div className="login-brand-info">
            <h2>Mediatize HRMS</h2>
            <span>Security Verification</span>
          </div>
        </div>

        {error && (
          <div className="login-alert-banner error" role="alert">
            <AlertCircle size={18} className="alert-ico" />
            <div className="alert-txt">{error}</div>
          </div>
        )}

        <form onSubmit={handleVerify} className="login-form-body">
          <div className="login-intro-text">
            <h3>Enter Verification Code</h3>
            <p>
              We dispatched a 6-digit code to: <br />
              <strong className="target-email">{email}</strong>
            </p>
          </div>

          <div className="login-field-box">
            <label htmlFor="verify-otp-digit-0">6-Digit Security Code</label>
            <div className="otp-digit-inputs" onPaste={handleOtpPaste}>
              {otpValues.map((digit, idx) => (
                <input
                  key={idx}
                  id={`verify-otp-digit-${idx}`}
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
          >
            {loading ? (
              <>
                <Loader2 size={18} className="spinner" />
                <span>Verifying your account...</span>
              </>
            ) : (
              <>
                <ShieldCheck size={18} />
                <span>Verify & Open Workspace</span>
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
              onClick={() => navigate("/login")}
              disabled={loading}
            >
              Change email
            </button>
          </div>
        </form>

        <div className="login-footer-nav">
          <button 
            type="button" 
            className="login-back-btn" 
            onClick={() => navigate("/login")}
          >
            <ArrowLeft size={15} />
            <span>Use a different corporate email</span>
          </button>
        </div>
      </div>
    </div>
  );
}