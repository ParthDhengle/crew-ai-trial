import axios from "axios";
import { getIdToken } from "@/hooks/useAuth"; 

const API_BASE = "http://127.0.0.1:8000";

export async function sendMessage(query: string, sessionId: string) {
  const token = await getIdToken();
  const res = await axios.post(
    `${API_BASE}/process_query`,
    { query, session_id: sessionId },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res.data;
}

export async function fetchChats(sessionId: string) {
  const token = await getIdToken();
  const res = await axios.get(`${API_BASE}/chats/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.data;
}
