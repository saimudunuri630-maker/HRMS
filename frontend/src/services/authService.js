import { broadcastMessage } from "./authSync";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const requestLoginOtp = async (email) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || "Failed to dispatch verification OTP.");
    }

    return data;
  } catch (error) {
    console.error("Error in requestLoginOtp:", error);
    throw error;
  }
};

export const verifyOtpCode = async (email, otp) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/verify-otp`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        otp: otp.trim(),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || "Invalid or expired passcode.");
    }

    if (data.access_token) {
      localStorage.setItem("hrms_token", data.access_token);
      localStorage.setItem("token", data.access_token);
    }
    if (data.user) {
      localStorage.setItem("hrms_user", JSON.stringify(data.user));
      localStorage.setItem("user", JSON.stringify(data.user));
    }

    broadcastMessage("AUTH_LOGIN", { user: data.user, token: data.access_token });

    return data;
  } catch (error) {
    console.error("Error in verifyOtpCode:", error);
    throw error;
  }
};

export const resendLoginOtp = async (email) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/resend-otp`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || "Failed to resend authentication code.");
    }

    return data;
  } catch (error) {
    console.error("Error in resendLoginOtp:", error);
    throw error;
  }
};