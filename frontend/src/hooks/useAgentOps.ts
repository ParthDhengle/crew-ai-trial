// src/hooks/useAgentOps.ts
import { useEffect, useState, useRef, useCallback } from "react";
import { useNova } from "@/context/NovaContext";
import type { AgentOp } from "@/api/types";
import { API_BASE_URL } from '@/api/client'; // Import base URL



export function useAgentOps() {
  const { state, dispatch } = useNova();
  const sessionId = state?.currentSession?.id;
  const [operations, setOperations] = useState<AgentOp[]>([]);
  const [agentStatus, setAgentStatus] = useState<string>(''); 
  const evtSourceRef = useRef<EventSource | null>(null);
  useEffect(() => {
    if (!sessionId) {
      setOperations([]);
      setAgentStatus('');
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
        console.log('SSE Event received:', payload); 
        switch (payload.type) {
          case "initial_state":
            setOperations(payload.operations || []);
            setAgentStatus('');
            break;

          case "ops_cleared":
            setOperations([]);
            setAgentStatus('');
            break;

          case "nova_thinking":
            setAgentStatus(payload.message || "Nova is thinking...");
            break;

          case "agentic_mode_activated":
            setAgentStatus(payload.message || "Nova agentic mode activated");
            // Operations should be created separately via op_created events
            break;

          case "op_created":
            setOperations(prev => {
              // Ensure no duplicates
              if (prev.find(op => op.id === payload.operation.id)) {
                return prev;
              }
              return [...prev, payload.operation];
            });
            break;

          case "op_updated":
            setOperations(prev => 
              prev.map(op => 
                op.id === payload.operation.id ? payload.operation : op
              )
            );
            break;

          case "operation_started":
            setOperations(prev => 
              prev.map(op => 
                op.id === payload.operation_id 
                  ? { ...op, status: 'running' as const, startTime: Date.now() }
                  : op
              )
            );
            setAgentStatus(`Running: ${payload.operation_name} (${payload.progress})`);
            break;

          case "operation_completed":
            setOperations(prev => 
              prev.map(op => 
                op.id === payload.operation_id 
                  ? { 
                      ...op, 
                      status: 'success' as const, 
                      progress: 100,
                      result: payload.result 
                    }
                  : op
              )
            );
            setAgentStatus(`Completed: ${payload.operation_name} (${payload.progress})`);
            break;

          case "operation_failed":
            setOperations(prev => 
              prev.map(op => 
                op.id === payload.operation_id 
                  ? { 
                      ...op, 
                      status: 'failed' as const, 
                      result: payload.error 
                    }
                  : op
              )
            );
            setAgentStatus(`Failed: ${payload.operation_name} (${payload.progress})`);
            break;

          case "all_operations_complete":
            setAgentStatus(`All ${payload.total_operations} operations completed`);
            // Clear status after a delay
            setTimeout(() => {
              setAgentStatus('');
            }, 3000);
            break;

          case "synthesis_complete":
            setAgentStatus("Response synthesized");

            dispatch({
              type: 'ADD_MESSAGE',
              payload: {
                sessionId: sessionId,
                message: {
                  id: Date.now().toString(),
                  role: 'assistant',
                  content: payload.response,
                  timestamp: Date.now()
                }
              }
            });
            // Clear status after delay
            setTimeout(() => {
              setAgentStatus('');
            }, 2000);
            break;

          case "direct_response":
            dispatch({
              type: 'ADD_MESSAGE',
              payload: {
                sessionId: sessionId,
                message: {
                  id: Date.now().toString(),
                  role: 'assistant',
                  content: payload.message,
                  timestamp: Date.now()
                }
              }
            });
            break;

          case "agentic_summary":
            console.log("Agentic execution summary:", payload.summary);
            break;

          case "agentic_error":
            console.error("Agentic execution error:", payload.error);
            setAgentStatus(`Error: ${payload.error}`);
            break;

          case "error":
            setAgentStatus(`Error: ${payload.message}`);
            break;

          default:
            console.log('Unhandled SSE event type:', payload.type);
        }
      } catch (e) {
        console.error("Failed to parse SSE payload", e);
      }
    };
    es.onerror = (err) => {
      console.error("SSE connection error", err);
      setAgentStatus("Connection error - retrying...");
      
      // Automatic reconnection with exponential backoff
      setTimeout(() => {
        if (sessionId && !evtSourceRef.current) {
          console.log("Attempting SSE reconnection...");
          // The useEffect will handle reconnection when component re-renders
        }
      }, 3000);
    };
    es.onopen = () => {
      console.log("SSE connection established for session:", sessionId);
      setAgentStatus('');
    };
    return () => {
      if (es) es.close();
      evtSourceRef.current = null;
    };
  }, [sessionId, dispatch]);
  const cancelOperation = useCallback(async (operationId: string) => {
   try {
      const response = await fetch(`${API_BASE_URL}/operations/${operationId}/status`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          // Add Authorization header if needed:
          // "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ status: "cancel_requested" })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Local optimistic update
      setOperations(prev => 
        prev.map(op => 
          op.id === operationId 
            ? ({ ...op, status: 'cancel_requested' }  as unknown as AgentOp)
            : op
        )
      );
      
      setAgentStatus(`Cancelling operation...`);
      
    } catch (e) {
      console.error("cancelOperation failed", e);
      setAgentStatus(`Failed to cancel operation`);
    }
  }, []);

  return { 
    operations, 
    cancelOperation, 
    agentStatus // Export status for display in UI
  };
}