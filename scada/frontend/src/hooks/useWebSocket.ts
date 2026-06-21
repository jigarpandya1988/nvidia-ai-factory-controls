import { useEffect, useRef } from 'react';
import { useProcessStore } from '../stores/useProcessStore';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { setCurrent, setConnected } = useProcessStore();

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      if (disposed) return;

      const ws = new WebSocket(`ws://${window.location.hostname}:4000/ws`);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!disposed) {
          setTimeout(connect, 2000);
        }
      };
      ws.onerror = () => ws.close();

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'process_data') {
            setCurrent(msg.data);
          }
        } catch {}
      };
    };

    connect();
    return () => {
      disposed = true;
      wsRef.current?.close();
    };
  }, []);

  const send = (cmd: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmd));
    }
  };

  return { send };
}
