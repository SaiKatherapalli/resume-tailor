export interface Contact {
  email: string;
  phone: string;
  location: string;
  links: string[];
}

export interface Education {
  degree: string;
  school: string;
  date: string;
  details: string;
}

export interface Experience {
  id: string;
  title: string;
  company: string;
  location: string;
  dates: string;
  max_bullets: number;
  bullets: string[];
}

export interface CareerBank {
  name: string;
  contact: Contact;
  summary: string;
  skills: Record<string, string[]>;
  experiences: Experience[];
  education: Education[];
}

export type JobStatus = 'queued' | 'running' | 'done' | 'failed';

export interface JobSummary {
  id: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  job_title: string | null;
  company: string | null;
  job_number: string | null;
}

export interface TailorResult {
  analysis: { job_title: string; company?: string; job_number?: string; responsibilities: string[]; keywords: string[] };
  resume: {
    summary: string;
    skills: { category: string; items: string[] }[];
    experiences: { experience_id: string; bullets: { text: string; source_ids: string[] }[] }[];
  };
  validation: {
    ok: boolean;
    issues: string[];
    fixes: string[];
    keyword_coverage: number;
    unused_keywords: string[];
  };
  attempts: number;
}

export interface Job extends JobSummary {
  job_description: string;
  result: TailorResult | null;
  error: string | null;
}
