// src/hooks/useAgentOps.ts
import { useEffect, useState, useRef, useCallback } from "react";
import { useNova } from "@/context/NovaContext";
import type { AgentOp } from "@/api/types";
import { API_BASE_URL } from '@/api/client'; // Import base URL



export function useAgentOps() {
  const { state } = useNova();
  const sessionId = state?.currentSession?.id;
  const [operations, setOperations] = useState<AgentOp[]>([]);
  const evtSourceRef = useRef<EventSource | null>(null);
  useEffect(() => {
    if (!sessionId) {
      setOperations([]);
      return;
    }
    // close previous
    if (evtSourceRef.current) {
      evtSourceRef.current.close();
      evtSourceRef.current = null;
    }
    const url = `${API_BASE_URL}/operations/stream?session_id=${encodeURIComponent(sessionId)}`; // Prefix with base
    const es = new EventSource(url, { withCredentials: true }); // Enable credentials for auth if needed
    evtSourceRef.current = es;
    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.type === "initial_state") {
          setOperations(payload.operations || []);
        } else if (payload.type === "op_created") {
          setOperations(prev => [...prev, payload.operation]);
        } else if (payload.type === "op_updated") {
          setOperations(prev => prev.map(op => op.id === payload.operation.id ? payload.operation : op));
        } else if (payload.type === "agentic_summary") {
          // optionally handle summary
          console.log("Agentic summary", payload.summary);
        } else if (payload.type === "agentic_error") {
          console.error("Agentic execution error:", payload.error);
        }
      } catch (e) {
        console.error("Failed to parse SSE payload", e);
      }
    };
    es.onerror = (err) => {
      console.error("SSE error", err);
      // Reconnect with backoff (optional)
      setTimeout(() => {
        // Recreate EventSource here if desired
      }, 3000);
    };
    return () => {
      if (es) es.close();
      evtSourceRef.current = null;
    };
  }, [sessionId]);
  const cancelOperation = useCallback(async (operationId: string) => {
    try {
      await fetch(`${API_BASE_URL}/operations/${operationId}/status?status=cancel_requested`, { // Prefix with base
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
          // Add Authorization: `Bearer ${token}` if auth is required
        }
      });
      // local state update will come from SSE when backend observes/cancels
    } catch (e) {
      console.error("cancelOperation failed", e);
    }
  }, []);
  return { operations, cancelOperation };
}