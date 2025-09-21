// Auth token management utilities
const AUTH_TOKEN_KEY = 'nova_auth_token';
const AUTH_UID_KEY = 'nova_auth_uid';

export const setAuthToken = (token: string) => {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem(AUTH_TOKEN_KEY);
};

export const removeAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_UID_KEY);
};

export const setAuthUID = (uid: string) => {
  localStorage.setItem(AUTH_UID_KEY, uid);
};

export const getAuthUID = (): string | null => {
  return localStorage.getItem(AUTH_UID_KEY);
};

export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};
