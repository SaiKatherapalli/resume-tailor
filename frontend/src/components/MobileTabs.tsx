import { Database, History, Wand2 } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const tabs = [
  { to: '/tailor', label: 'Tailor', icon: Wand2 },
  { to: '/career-bank', label: 'Career bank', icon: Database },
  { to: '/jobs', label: 'History', icon: History }, // also active on /jobs/:id
];

/** Phone only: the three pages in thumb reach, like an app. The desktop navbar has the same links. */
export default function MobileTabs() {
  return (
    <nav
      aria-label="Main"
      className="md:hidden print:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur border-t border-slate-200 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_-12px_rgba(15,23,42,0.25)]"
    >
      <ul className="grid grid-cols-3">
        {tabs.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                `relative flex flex-col items-center justify-center gap-1 min-h-[60px] text-[11px] font-semibold transition-colors active:bg-slate-50 ${
                  isActive ? 'text-amber-600' : 'text-slate-500'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`absolute top-0 h-0.5 w-10 rounded-full bg-amber-500 transition-opacity ${isActive ? 'opacity-100' : 'opacity-0'}`}
                  />
                  <Icon size={22} strokeWidth={isActive ? 2.4 : 2} />
                  {label}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
