import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/api";

export function useGuardianFeed() {
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const base = getApiBaseUrl();
    const wsUrl = base.replace(/^http/, "ws") + "/ws/scams";

    let ws: WebSocket;
    let reconnectTimeout: any;

    const connect = () => {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          // Standardize payload if needed
          const event = {
            id: payload.event_id,
            source: payload.source,
            decision: payload.decision,
            risk: payload.risk_score,
            reasons: payload.reasons || [],
            timestamp: new Date().toISOString()
          };
          setEvents((prev) => [event, ...prev].slice(0, 20));
        } catch (err) {
          console.error("WS parse error", err);
        }
      };

      ws.onclose = () => {
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        console.error("WS error", err);
        ws.close();
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  return events;
}
