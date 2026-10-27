import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Trash2 } from 'lucide-react';
import { ApiError, deleteJob, listJobs } from '../lib/api';
import type { JobSummary } from '../types';
import StatusBadge from '../components/StatusBadge';

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
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">History</h1>
        <Link to="/tailor" className="btn-primary">
          New tailoring
        </Link>
      </div>

      {error && <p className="text-red-600">{error}</p>}
      {!jobs && !error && <Loader2 className="animate-spin text-slate-400 mx-auto mt-10" />}
      {jobs?.length === 0 && <p className="text-slate-600">No tailored resumes yet.</p>}

      <ul className="space-y-2">
        {jobs?.map((j) => (
          <li key={j.id} className="card !p-4 flex items-center justify-between gap-3">
            <Link to={`/jobs/${j.id}`} className="flex-1 flex items-center gap-3 min-w-0">
              <StatusBadge status={j.status} />
              <span className="text-sm text-slate-700 truncate">{new Date(j.created_at).toLocaleString()}</span>
            </Link>
            <button onClick={() => remove(j.id)} className="text-slate-400 hover:text-red-600" aria-label="Delete job">
              <Trash2 size={16} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
