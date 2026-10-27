import type { JobStatus } from '../types';

const styles: Record<JobStatus, string> = {
  queued: 'bg-slate-100 text-slate-600',
  running: 'bg-blue-100 text-blue-700',
  done: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
};

export default function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${styles[status]}`}>
      {status}
    </span>
  );
}
