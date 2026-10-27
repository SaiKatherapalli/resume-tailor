import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronRight, FileClock, Plus, Trash2 } from 'lucide-react';
import { ApiError, deleteJob, listJobs } from '../lib/api';
import type { JobSummary } from '../types';
import StatusBadge from '../components/StatusBadge';
import PageHeader from '../components/PageHeader';

function ago(iso: string): string {
  // The server sends UTC without a "Z"
  const t = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`).getTime();
  const mins = Math.round((Date.now() - t) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

export default function History() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Could not load history.'));
  }, []);

  const remove = async (id: string) => {
    if (!window.confirm('Delete this job?')) return;
    await deleteJob(id);
    setJobs((prev) => prev?.filter((j) => j.id !== id) ?? null);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-10 relative">
      <div className="flex justify-end sm:absolute sm:right-0 sm:top-0 sm:z-10">
        <Link to="/tailor" className="btn-primary">
          <Plus size={16} /> New tailoring
        </Link>
      </div>

      <PageHeader center eyebrow="Your tailored resumes" subtitle="Open a past job to see the result or download it again." />

      {error && <p className="alert-error">{error}</p>}

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.05 }}
        className="relative overflow-hidden rounded-2xl bg-white border border-slate-300 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_32px_64px_-28px_rgba(15,23,42,0.28)]"
      >
        <div className="h-1 bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500" />

        {!jobs && !error && (
          <ul className="divide-y divide-slate-200">
            {[0, 1, 2].map((i) => (
              <li key={i} className="px-6 sm:px-9 py-6">
                <div className="h-9 rounded-lg bg-slate-100 animate-pulse" />
              </li>
            ))}
          </ul>
        )}

        {jobs?.length === 0 && (
          <div className="text-center px-6 py-16">
            <div className="mx-auto w-14 h-14 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center">
              <FileClock size={26} />
            </div>
            <h2 className="mt-4 font-bold text-lg">Nothing here yet</h2>
            <p className="text-slate-600 text-sm mt-1">Your tailored resumes will show up here.</p>
          </div>
        )}

        <ul className="divide-y divide-slate-200">
          {jobs?.map((j, i) => (
            <motion.li
              key={j.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.04 }}
              className="group flex items-center transition hover:bg-amber-50/50"
            >
              <Link to={`/jobs/${j.id}`} className="flex-1 flex items-center gap-4 min-w-0 pl-6 sm:pl-9 pr-3 py-5">
                <div className="icon-chip">
                  <FileClock size={18} />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold truncate">{j.job_title ?? 'Tailored resume'}</p>
                  <p className="text-xs text-slate-500 truncate" title={new Date(j.created_at + (j.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}>
                    {[j.company, ago(j.created_at)].filter(Boolean).join(' · ')}
                  </p>
                </div>
                <div className="ml-auto">
                  <StatusBadge status={j.status} />
                </div>
                <ChevronRight size={18} className="text-slate-300 transition group-hover:text-amber-500 group-hover:translate-x-0.5" />
              </Link>
              <button onClick={() => remove(j.id)} className="pl-3 pr-6 sm:pr-9 self-stretch text-slate-300 hover:text-red-600 transition" aria-label="Delete job">
                <Trash2 size={16} />
              </button>
            </motion.li>
          ))}
        </ul>

      </motion.div>
    </div>
  );
}
