import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CheckCircle2, Download, Loader2, Trash2 } from 'lucide-react';
import { ApiError, deleteJob, downloadJobFile, getCareerBank, getJob } from '../lib/api';
import type { CareerBank, Job } from '../types';
import ResumePreview from '../components/ResumePreview';
import StatusBadge from '../components/StatusBadge';

const POLL_MS = 2500;

export default function JobView() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [bank, setBank] = useState<CareerBank | null>(null);
  const [error, setError] = useState('');
  const [downloadError, setDownloadError] = useState('');

  // Poll until the job is done or failed
  useEffect(() => {
    let stopped = false;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const j = await getJob(id);
        if (stopped) return;
        setJob(j);
        if (j.status === 'queued' || j.status === 'running') timer = window.setTimeout(tick, POLL_MS);
      } catch (e) {
        if (!stopped) setError(e instanceof ApiError ? e.message : 'Could not load this job.');
      }
    };
    tick();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [id]);

  useEffect(() => {
    getCareerBank().then(setBank).catch(() => undefined);
  }, []);

  // PDF = the browser prints only the resume ("Save as PDF"). No LaTeX needed on the server.
  const printPdf = () => {
    const previous = document.title;
    const name = bank?.name ?? 'Resume';
    document.title = `${name} - ${job?.result?.analysis.job_title ?? 'Resume'}`; // becomes the PDF file name
    const restore = () => {
      document.title = previous;
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
  };

  // PDF: ask the server first (LaTeX, same look as the .tex). If it has no compiler (503), print from the browser.
  const downloadPdf = async () => {
    setDownloadError('');
    try {
      await downloadJobFile(id, 'pdf');
    } catch (e) {
      if (e instanceof ApiError && (e.status === 503 || e.status === 0)) printPdf();
      else setDownloadError(e instanceof ApiError ? e.message : 'Download failed.');
    }
  };

  const download = async (kind: 'tex') => {
    setDownloadError('');
    try {
      await downloadJobFile(id, kind);
    } catch (e) {
      setDownloadError(e instanceof ApiError ? e.message : 'Download failed.');
    }
  };

  const remove = async () => {
    if (!window.confirm('Delete this job?')) return;
    await deleteJob(id);
    navigate('/jobs');
  };

  if (error) return <p className="text-red-600">{error}</p>;
  if (!job) return <Loader2 className="animate-spin text-slate-400 mx-auto mt-16" />;

  const result = job.result;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex items-center gap-3">
          <Link to="/jobs" className="text-slate-500 hover:text-slate-900">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-2xl font-bold">{result?.analysis.job_title ?? 'Tailoring job'}</h1>
          <StatusBadge status={job.status} />
        </div>
        <div className="flex gap-2">
          {job.status === 'done' && (
            <>
              <button className="btn-outline" onClick={() => download('tex')}>
                <Download size={16} /> .tex
              </button>
              <button className="btn-primary" onClick={downloadPdf}>
                <Download size={16} /> PDF
              </button>
            </>
          )}
          <button className="btn-outline !text-red-600" onClick={remove} aria-label="Delete job">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {downloadError && <p className="print:hidden text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{downloadError}</p>}

      {(job.status === 'queued' || job.status === 'running') && (
        <div className="card flex items-center gap-3">
          <Loader2 className="animate-spin text-amber-500" />
          <div>
            <p className="font-semibold">{job.status === 'queued' ? 'Waiting to start…' : 'Tailoring your resume…'}</p>
            <p className="text-sm text-slate-600">Analyzing the job, finding your best bullets, rewriting and checking them.</p>
          </div>
        </div>
      )}

      {job.status === 'failed' && (
        <div className="card border-red-200 bg-red-50 text-red-800">
          <p className="font-semibold">This job failed</p>
          <p className="text-sm mt-1">{job.error ?? 'Unknown error.'}</p>
          <Link to="/tailor" className="btn-primary mt-3">
            Try again
          </Link>
        </div>
      )}

      {result && (
        <div className="grid gap-5 lg:grid-cols-[1fr_320px] print:block">
          <ResumePreview bank={bank} resume={result.resume} />

          <aside className="space-y-4 print:hidden">
            <div className="card">
              <h3 className="font-semibold mb-2">Keyword match</h3>
              <p className="text-3xl font-bold text-amber-500">{Math.round(result.validation.keyword_coverage * 100)}%</p>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {result.analysis.keywords.map((k) => {
                  const missing = result.validation.unused_keywords.includes(k);
                  return (
                    <span
                      key={k}
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        missing ? 'bg-slate-100 text-slate-500' : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {k}
                    </span>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-2">Grey keywords were not used because they are not in your career bank.</p>
            </div>

            <div className="card">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                {result.validation.ok ? (
                  <CheckCircle2 size={18} className="text-emerald-600" />
                ) : (
                  <AlertTriangle size={18} className="text-amber-600" />
                )}
                Validation
              </h3>
              <p className="text-sm text-slate-600">
                {result.validation.ok ? 'All checks passed' : 'Some issues remain'} after {result.attempts} attempt
                {result.attempts === 1 ? '' : 's'}.
              </p>
              {result.validation.issues.length > 0 && (
                <ul className="list-disc pl-5 mt-2 text-sm text-amber-800 space-y-1">
                  {result.validation.issues.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              )}
              {result.validation.fixes.length > 0 && (
                <details className="mt-2 text-sm text-slate-600">
                  <summary className="cursor-pointer">{result.validation.fixes.length} automatic fixes</summary>
                  <ul className="list-disc pl-5 mt-1 space-y-1">
                    {result.validation.fixes.map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>

            <div className="card">
              <h3 className="font-semibold mb-2">What the job asks for</h3>
              <ul className="list-disc pl-5 text-sm text-slate-700 space-y-1">
                {result.analysis.responsibilities.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
