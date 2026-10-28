export type RealtimeNotification = { type: string; payload: unknown };

type WireNotification = { id: number; message: RealtimeNotification };

export function connectRealtime(realtimeUrl: string | undefined, onNotifications: (notifications: RealtimeNotification[]) => void) {
  let socket: WebSocket | undefined;
  let stopped = false;
  let retry = 1000;
  let reconnectTimer: number | undefined;
  let last = Number(sessionStorage.getItem("toova.bus.last") || 0);

  // ponytail: one socket per tab; move this transport into SharedWorker when multi-tab connection pressure matters.
  const connect = () => {
    if (stopped) return;
    const url = realtimeUrl || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/websocket`;
    socket = new WebSocket(url);
    socket.addEventListener("open", () => {
      retry = 1000;
      socket?.send(JSON.stringify({ event_name: "subscribe", data: { channels: [], last } }));
    });
    socket.addEventListener("message", (event) => {
      try {
        const notifications = JSON.parse(String(event.data)) as WireNotification[];
        if (!Array.isArray(notifications) || !notifications.length) return;
        last = notifications[notifications.length - 1].id;
        sessionStorage.setItem("toova.bus.last", String(last));
        onNotifications(notifications.map((notification) => notification.message));
      } catch { /* Ignore malformed transport frames; native reconnect remains active. */ }
    });
    socket.addEventListener("close", () => {
      if (stopped) return;
      reconnectTimer = window.setTimeout(connect, retry);
      retry = Math.min(Math.round(retry * 1.5), 30000);
    });
  };

  connect();
  return () => {
    stopped = true;
    window.clearTimeout(reconnectTimer);
    socket?.close(1000);
  };
}
