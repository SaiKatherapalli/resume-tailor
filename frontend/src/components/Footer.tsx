import { ArrowUp, FileText, KeyRound, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  authed: boolean;
  onGetStarted: () => void;
}

const links = [
  { to: '/tailor', label: 'Tailor a resume' },
  { to: '/career-bank', label: 'Career bank' },
  { to: '/jobs', label: 'History' },
];

export default function Footer({ authed, onGetStarted }: Props) {
  const linkClass = 'inline-block py-1 text-slate-300 hover:text-amber-400 transition-colors';

  return (
    <footer className="print:hidden mt-10 bg-slate-900 text-slate-300">
      <div className="h-px bg-gradient-to-r from-transparent via-amber-500/70 to-transparent" />

      <div className="max-w-6xl mx-auto px-5 sm:px-8 lg:px-12 pt-10 pb-8 grid gap-9 sm:grid-cols-2 md:grid-cols-[1.5fr_1fr_1.2fr]">
        <div className="sm:col-span-2 md:col-span-1">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-slate-800 text-amber-400">
              <FileText size={18} />
            </div>
            <span className="font-semibold text-white text-lg">
              Resume<span className="text-amber-400">Tailor</span>
            </span>
          </div>
          <p className="mt-3 text-sm text-slate-400 max-w-xs leading-relaxed">
            Your resume, rewritten for each job. Only facts from your own career history.
          </p>
        </div>

        <div>
          <h4 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Product</h4>
          <ul className="mt-3 text-sm">
            {authed ? (
              links.map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className={linkClass}>
                    {l.label}
                  </Link>
                </li>
              ))
            ) : (
              <li>
                <button onClick={onGetStarted} className={linkClass}>
                  Get started
                </button>
              </li>
            )}
          </ul>
        </div>

        <div>
          <h4 className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Your data</h4>
          <ul className="mt-3 space-y-2.5 text-sm text-slate-400">
            <li className="flex gap-2.5">
              <ShieldCheck size={16} className="mt-0.5 shrink-0 text-amber-400" />
              Only facts from your career bank are used.
            </li>
            <li className="flex gap-2.5">
              <KeyRound size={16} className="mt-0.5 shrink-0 text-amber-400" />
              Your own Groq key is never saved in our database.
            </li>
          </ul>
        </div>
      </div>

      {/* On a phone the tab bar covers the bottom, so signed-in users get extra room below. */}
      <div className="border-t border-slate-800">
        <div
          className={`max-w-6xl mx-auto px-5 sm:px-8 lg:px-12 pt-4 flex items-center justify-between gap-3 text-xs text-slate-500 ${
            authed ? 'pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:pb-4' : 'pb-[max(1rem,env(safe-area-inset-bottom))]'
          }`}
        >
          <p>© {new Date().getFullYear()} ResumeTailor</p>
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="inline-flex items-center gap-1 py-1 text-slate-400 hover:text-amber-400 transition-colors"
          >
            Back to top <ArrowUp size={14} />
          </button>
        </div>
      </div>
    </footer>
  );
}
