import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, Wand2 } from 'lucide-react';
import { ApiError, createJob, getCareerBank } from '../lib/api';
import GroqKeyField from '../components/GroqKeyField';

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
  const valid = length >= MIN_CHARS && length <= MAX_CHARS;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Tailor your resume</h1>
        <p className="text-slate-600 text-sm mt-1">Paste the job description. It takes about 20 to 60 seconds.</p>
      </div>

      {hasBank === false && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-sm px-4 py-3">
          You need a career bank first.{' '}
          <Link to="/career-bank" className="font-semibold underline">
            Upload your resume
          </Link>
          .
        </div>
      )}

      <div className="card space-y-4">
        <div>
          <label className="label">Job description</label>
          <textarea
            className="input min-h-[260px] resize-y"
            placeholder="Paste the full job description here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <p className={`text-xs mt-1 ${length > MAX_CHARS ? 'text-red-600' : 'text-slate-500'}`}>
            {length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters (at least {MIN_CHARS})
          </p>
        </div>

        <GroqKeyField />

        {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

        <button className="btn-primary" disabled={!valid || busy || hasBank === false} onClick={submit}>
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
          {busy ? 'Starting…' : 'Tailor my resume'}
        </button>
      </div>
    </div>
  );
}
