"use client";

import { useEffect, useRef, useState } from "react";
import { PUBLIC_BACKEND_URL, type EcsEvent } from "./api";

// Subscribes to the backend SSE live-tail stream while `enabled` is true.
// Keeps the most recent `max` events, newest first.
export function useSse(enabled: boolean, max = 200): EcsEvent[] {
  const [events, setEvents] = useState<EcsEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) {
      sourceRef.current?.close();
      sourceRef.current = null;
      return;
    }

    const source = new EventSource(`${PUBLIC_BACKEND_URL}/events/stream`);
    sourceRef.current = source;

    source.onmessage = (e: MessageEvent<string>) => {
      try {
        const event = JSON.parse(e.data) as EcsEvent;
        setEvents((prev) => [event, ...prev].slice(0, max));
      } catch {
        // ignore heartbeat / malformed frames
      }
    };

    source.onerror = () => {
      // EventSource auto-reconnects; nothing to do here.
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [enabled, max]);

  return events;
}
