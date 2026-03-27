import { useState, useEffect, useRef, useCallback } from "react";

export function useWebSocket(url) {
  const [state, setState]         = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef  = useRef(null);
  const retry  = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        clearTimeout(retry.current);
      };

      ws.onmessage = (e) => {
        try { setState(JSON.parse(e.data)); } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        retry.current = setTimeout(connect, 2000); // auto-reconnect
      };

      ws.onerror = () => ws.close();
    } catch (err) {
      setConnected(false);
      retry.current = setTimeout(connect, 2000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retry.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { state, connected };
}