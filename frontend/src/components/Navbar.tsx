import { useState } from 'react';
import { FileText, LogIn, LogOut, Menu, X } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 text-sm transition-colors ${isActive ? 'text-amber-400' : 'text-slate-400 hover:text-amber-400'}`;

  return (
    <nav className="w-full bg-slate-900 text-slate-200 sticky top-0 z-50 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <button onClick={() => navigate('/')} className="flex items-center gap-2">
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
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-amber-500 text-slate-900 font-semibold hover:bg-amber-600 transition"
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
              <span className="text-xs text-slate-500 max-w-[180px] truncate">{getEmail()}</span>
              <button
                onClick={onSignOut}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 text-sm font-medium"
              >
                <LogOut size={16} /> Sign out
              </button>
            </div>
            <button className="md:hidden p-2 text-slate-300" onClick={() => setOpen(!open)} aria-label="Toggle navigation">
              {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </>
        )}
      </div>

      {authed && open && (
        <div className="md:hidden px-4 py-3 space-y-1 bg-slate-900 border-t border-slate-800">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkClass} onClick={() => setOpen(false)}>
              <div className="py-1">{l.label}</div>
            </NavLink>
          ))}
          <button onClick={onSignOut} className="px-3 py-2 text-sm text-slate-300 hover:text-orange-400">
            Sign out
          </button>
        </div>
      )}
    </nav>
  );
}
