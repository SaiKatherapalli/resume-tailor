import type { CareerBank, Job, JobSummary } from '../types';

export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const TOKEN_KEY = 'access_token';
const EMAIL_KEY = 'user_email';
const GROQ_KEY = 'groq_api_key';

// ---------------------------------------------------------------- local storage

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const getEmail = (): string | null => localStorage.getItem(EMAIL_KEY);
export const isAuthenticated = (): boolean => Boolean(getToken());

/** Optional: the user's own Groq key. Sent with each request that calls the LLM, never to our database. */
export const getGroqKey = (): string => localStorage.getItem(GROQ_KEY) ?? '';
export function setGroqKey(key: string): void {
  if (key.trim()) localStorage.setItem(GROQ_KEY, key.trim());
  else localStorage.removeItem(GROQ_KEY);
}

function saveSession(token: string, email: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EMAIL_KEY, email);
  window.dispatchEvent(new Event('auth-change'));
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EMAIL_KEY);
  window.dispatchEvent(new Event('auth-change'));
}

// ---------------------------------------------------------------- core fetch

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

/** FastAPI errors are {detail: "text"} or, for validation errors, {detail: [{loc, msg}, ...]}. */
function errorText(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`.replace(/^: /, ''))
      .join('; ');
  }
  return fallback;
}

async function request(path: string, init: RequestInit = {}, withGroqKey = false): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const groq = getGroqKey();
  if (withGroqKey && groq) headers.set('X-Groq-Api-Key', groq);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError('Cannot reach the server. Is the backend running?', 0);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    if (res.status === 401 && token && !path.startsWith('/auth/login')) logout(); // token expired
    throw new ApiError(errorText(data?.detail, res.statusText), res.status);
  }
  return res;
}

const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

// ---------------------------------------------------------------- auth

export async function register(email: string, password: string): Promise<void> {
  await request('/auth/register', { method: 'POST', ...json({ email, password }) });
}

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams({ username: email, password });
  const res = await request('/auth/login', { method: 'POST', body: form });
  const data = await res.json();
  saveSession(data.access_token, email.trim().toLowerCase());
}

// ---------------------------------------------------------------- career bank

/** Returns null when the user has no career bank yet. */
export async function getCareerBank(): Promise<CareerBank | null> {
  try {
    return await (await request('/career-bank')).json();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export async function saveCareerBank(bank: CareerBank): Promise<CareerBank> {
  return (await request('/career-bank', { method: 'PUT', ...json(bank) })).json();
}

/** Upload a resume; the server returns a career bank draft (not saved yet). */
export async function importResume(file: File): Promise<CareerBank> {
  const form = new FormData();
  form.append('file', file);
  return (await request('/career-bank/import', { method: 'POST', body: form }, true)).json();
}

// ---------------------------------------------------------------- jobs

export async function createJob(jobDescription: string): Promise<Job> {
  return (await request('/jobs', { method: 'POST', ...json({ job_description: jobDescription }) }, true)).json();
}

export async function getJob(id: string): Promise<Job> {
  return (await request(`/jobs/${id}`)).json();
}

export async function listJobs(): Promise<JobSummary[]> {
  return (await request('/jobs?limit=50')).json();
}

export async function deleteJob(id: string): Promise<void> {
  await request(`/jobs/${id}`, { method: 'DELETE' });
}

/** First name + role + company, e.g. Sai_Software_Engineer_Amazon_resume (no extension). */
export function resumeFileName(fullName: string | undefined, jobTitle: string | undefined, company: string | undefined): string {
  const clean = (s: string | undefined) => (s ?? '').normalize('NFKD').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  const first = clean((fullName ?? '').trim().split(/\s+/)[0]);
  const firstName = first.charAt(0).toUpperCase() + first.slice(1).toLowerCase(); // SAI -> Sai
  return [firstName, clean(jobTitle), clean(company), 'resume'].filter(Boolean).join('_');
}

export async function downloadJobFile(id: string, kind: 'tex' | 'pdf', baseName?: string): Promise<void> {
  const res = await request(`/jobs/${id}/${kind}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement('a');
  a.href = url;
  a.download = `${baseName || `resume-${id.slice(0, 8)}`}.${kind}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
