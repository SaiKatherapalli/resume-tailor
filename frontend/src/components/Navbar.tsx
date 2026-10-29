import { useEffect, useRef, useState } from 'react';
import { FileText, LogIn, LogOut } from 'lucide-react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { getEmail } from '../lib/api';

interface Props {
  authed: boolean;
  onSignIn: () => void;
  onSignOut: () => void;
}

const links = [
  { to: '/tailor', label: 'Tailor Resume' },
  { to: '/career-bank', label: 'Career Bank' },
  { to: '/jobs', label: 'History' },
];

export default function Navbar({ authed, onSignIn, onSignOut }: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const email = getEmail() ?? '';

  // Close the account menu on navigation, on Escape, and when tapping anywhere else.
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onTap = (e: PointerEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', onTap);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onTap);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 text-sm transition-colors ${isActive ? 'text-amber-400' : 'text-slate-400 hover:text-amber-400'}`;

  // `sticky` only works if no parent wraps this element, so App renders <Navbar> directly.
  return (
    <nav className="print:hidden w-full sticky top-0 z-50 bg-slate-900/95 backdrop-blur text-slate-200 border-b border-slate-800 pt-[env(safe-area-inset-top)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <button onClick={() => navigate('/')} className="flex items-center gap-2" aria-label="ResumeTailor home">
          <div className="p-2 rounded-lg bg-slate-800 text-amber-400">
            <FileText size={20} />
          </div>
          <span className="font-semibold text-white text-lg">
            Resume<span className="text-amber-400">Tailor</span>
          </span>
        </button>

        {!authed ? (
          <button
            onClick={onSignIn}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-amber-500 text-slate-900 font-semibold hover:bg-amber-600 active:scale-95 transition"
          >
            <LogIn size={16} /> Sign in
          </button>
        ) : (
          <>
            <div className="hidden md:flex items-center gap-3">
              {links.map((l) => (
                <NavLink key={l.to} to={l.to} className={linkClass}>
                  {l.label}
                </NavLink>
              ))}
              <span className="text-xs text-slate-500 max-w-[180px] truncate">{email}</span>
              <button
                onClick={onSignOut}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 text-sm font-medium"
              >
                <LogOut size={16} /> Sign out
              </button>
            </div>

            {/* Phone: the pages are in the bottom tab bar, so the top bar only needs the account. */}
            <div className="md:hidden relative" ref={menuRef}>
              <button
                onClick={() => setOpen((o) => !o)}
                aria-label="Account menu"
                aria-expanded={open}
                className="w-10 h-10 rounded-full bg-slate-800 text-amber-400 font-bold uppercase border border-slate-700 flex items-center justify-center active:scale-95 transition"
              >
                {email.charAt(0) || '?'}
              </button>
              {open && (
                <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white text-slate-900 shadow-2xl border border-slate-200 p-2">
                  <div className="px-3 py-2">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Signed in as</p>
                    <p className="text-sm font-semibold truncate">{email}</p>
                  </div>
                  <button
                    onClick={onSignOut}
                    className="w-full flex items-center gap-2 px-3 py-3 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-50 active:bg-red-100"
                  >
                    <LogOut size={16} /> Sign out
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </nav>
  );
}
