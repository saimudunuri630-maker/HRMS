// Cross-tab synchronization service for authentication and notifications

const CHANNEL_NAME = "hrms_cross_tab_sync";

const getChannel = () => {
  if (typeof window !== "undefined" && "BroadcastChannel" in window) {
    try {
      return new BroadcastChannel(CHANNEL_NAME);
    } catch {
      return null;
    }
  }
  return null;
};

export const broadcastChannel = getChannel();

export const broadcastMessage = (type, payload = {}) => {
  if (broadcastChannel) {
    try {
      broadcastChannel.postMessage({ type, ...payload, timestamp: Date.now() });
    } catch (e) {
      console.warn("BroadcastChannel error:", e);
    }
  }
};

export const broadcastNotificationCount = (count, delta) => {
  if (typeof window !== "undefined") {
    if (count !== undefined && count !== null) {
      localStorage.setItem("hrms_unread_notifs", String(count));
    }
    window.dispatchEvent(
      new CustomEvent("unreadNotificationsUpdated", {
        detail: { count, delta },
      })
    );
  }
  broadcastMessage("NOTIF_COUNT_UPDATE", { unreadCount: count, delta });
};
