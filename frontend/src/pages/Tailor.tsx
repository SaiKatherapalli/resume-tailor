import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronRight, Loader2, Wand2 } from 'lucide-react';
import { ApiError, createJob, getCareerBank } from '../lib/api';
import GroqKeyField from '../components/GroqKeyField';
import PageHeader from '../components/PageHeader';

const MIN_CHARS = 50;
const MAX_CHARS = 20_000;

export default function Tailor() {
  const navigate = useNavigate();
  const [hasBank, setHasBank] = useState<boolean | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getCareerBank()
      .then((b) => setHasBank(b !== null))
      .catch(() => setHasBank(true)); // don't block the page if this check fails
  }, []);

  const submit = async () => {
    setError('');
    setBusy(true);
    try {
      const job = await createJob(text.trim());
      navigate(`/jobs/${job.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong.');
      setBusy(false);
    }
  };

  const length = text.trim().length;
  const tooLong = length > MAX_CHARS;
  const valid = length >= MIN_CHARS && !tooLong;
  const progress = tooLong ? 100 : Math.min(100, (length / MIN_CHARS) * 100);

  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <PageHeader
        center
        eyebrow="Tailor your resume"
        subtitle="Paste a job description. In about 20 to 60 seconds you get a resume rewritten for it, using only your own facts."
      />

      {hasBank === false && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-sm px-4 py-3">
          You need a career bank first.{' '}
          <Link to="/career-bank" className="font-semibold underline">
            Upload your resume
          </Link>
          .
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.05 }}
        className="relative overflow-hidden rounded-2xl bg-white border border-slate-300 shadow-[0_1px_2px_rgba(15,23,42,0.05),0_32px_64px_-28px_rgba(15,23,42,0.28)]"
      >
        <div className="h-1 bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500" />

        <div className="px-6 sm:px-9 pt-8 pb-6">
          <label htmlFor="jd" className="label">
            Job description
          </label>
          <textarea
            id="jd"
            rows={7}
            className="w-full min-h-[170px] resize-y rounded-xl border border-slate-200 bg-slate-50/70 px-5 py-4 text-[15px] leading-7 text-slate-900 placeholder:text-slate-400 transition focus:outline-none focus:bg-white focus:border-slate-900 focus:ring-4 focus:ring-slate-900/10"
            placeholder="Paste the full job description here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="mt-3 h-[3px] rounded-full bg-slate-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${tooLong ? 'bg-red-500' : valid ? 'bg-emerald-500' : 'bg-amber-400'}`}
              style={{ width: `${progress}%` }}
            />
          </div>

          {error && <p className="alert-error mt-5">{error}</p>}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 px-6 sm:px-9 py-5 bg-slate-50 border-t border-slate-200">
          <div className="text-sm">
            <p className="font-semibold text-slate-700">{valid ? 'Ready when you are.' : `Add at least ${MIN_CHARS} characters.`}</p>
            <p className={`text-xs tabular-nums mt-0.5 ${tooLong ? 'text-red-600' : 'text-slate-500'}`}>
              {length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
            </p>
          </div>
          <button className="btn-primary !px-6 !py-3" disabled={!valid || busy || hasBank === false} onClick={submit}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
            {busy ? 'Starting…' : 'Tailor my resume'}
          </button>
        </div>

        <details className="group px-6 sm:px-9 py-4 border-t border-slate-200">
          <summary className="flex items-center gap-1.5 cursor-pointer list-none text-sm font-semibold text-slate-600 hover:text-slate-900 transition [&::-webkit-details-marker]:hidden">
            <ChevronRight size={16} className="transition-transform group-open:rotate-90" />
            Use your own Groq key (optional)
          </summary>
          <div className="mt-4 pb-2">
            <GroqKeyField />
          </div>
        </details>
      </motion.div>
    </div>
  );
}
