import { ChangeEvent, useEffect, useState } from 'react';
import { Briefcase, ChevronRight, GraduationCap, Loader2, Plus, Save, Sparkles, Trash2, Upload, User, Wrench } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { ApiError, getCareerBank, importResume, saveCareerBank } from '../lib/api';
import type { CareerBank, Education, Experience } from '../types';
import GroqKeyField from '../components/GroqKeyField';

const emptyExperience = (n: number): Experience => ({
  id: `job_${n}`,
  title: '',
  company: '',
  location: '',
  dates: '',
  max_bullets: 6,
  bullets: [''],
});

const emptyBank = (): CareerBank => ({
  name: '',
  contact: { email: '', phone: '', location: '', links: [] },
  summary: '',
  skills: {},
  experiences: [emptyExperience(1)],
  education: [],
});

const splitList = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean);

export default function CareerBankPage() {
  const [bank, setBank] = useState<CareerBank | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(false); // imported but not saved yet
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    getCareerBank()
      .then(setBank)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Could not load your career bank.'))
      .finally(() => setLoading(false));
  }, []);

  const fail = (e: unknown) => setError(e instanceof ApiError ? e.message : 'Something went wrong.');

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (bank && !window.confirm('This replaces the form with the imported resume (not saved until you click Save). Continue?')) return;
    setError('');
    setNotice('');
    setImporting(true);
    try {
      setBank(await importResume(file));
      setDraft(true);
      setNotice('Imported. Check every field carefully, then click Save.');
    } catch (err) {
      fail(err);
    } finally {
      setImporting(false);
    }
  };

  const save = async () => {
    if (!bank) return;
    setError('');
    setNotice('');
    setSaving(true);
    try {
      setBank(await saveCareerBank(bank));
      setDraft(false);
      setNotice('Saved.');
    } catch (err) {
      fail(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Loader2 className="animate-spin text-slate-400 mx-auto mt-16" />;

  const set = (patch: Partial<CareerBank>) => setBank((b) => (b ? { ...b, ...patch } : b));
  const setExp = (i: number, patch: Partial<Experience>) =>
    set({ experiences: bank!.experiences.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
  const setEdu = (i: number, patch: Partial<Education>) =>
    set({ education: bank!.education.map((x, j) => (j === i ? { ...x, ...patch } : x)) });

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <PageHeader
        center
        eyebrow="Career bank"
        subtitle="Everything true about your career. The AI only uses facts from here, so keep it accurate."
      />

      <div className="panel space-y-6">
        <div>
          <label className="label">Import from a resume (.pdf, .tex, .txt, .md, max 2 MB)</label>
          <label className={`btn-outline cursor-pointer w-full sm:w-auto ${importing ? 'opacity-50 pointer-events-none' : ''}`}>
            {importing ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {importing ? 'Reading your resume…' : 'Choose file'}
            <input type="file" accept=".pdf,.tex,.txt,.md" className="hidden" onChange={onFile} />
          </label>
        </div>
        <details className="group border-t border-slate-200 pt-5">
          <summary className="flex items-center gap-1.5 cursor-pointer list-none text-sm font-semibold text-slate-600 hover:text-slate-900 transition [&::-webkit-details-marker]:hidden">
            <ChevronRight size={16} className="transition-transform group-open:rotate-90" />
            Use your own Groq key (optional)
          </summary>
          <div className="mt-4">
            <GroqKeyField />
          </div>
        </details>
      </div>

      {error && <p className="alert-error">{error}</p>}
      {notice && <p className="alert-ok">{notice}</p>}

      {!bank ? (
        <div className="panel text-center !py-14 space-y-3">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center">
            <Sparkles size={26} />
          </div>
          <p className="text-slate-600">No career bank yet. Import a resume above, or start from scratch.</p>
          <button className="btn-outline" onClick={() => setBank(emptyBank())}>
            Start from scratch
          </button>
        </div>
      ) : (
        <>
          <section className="panel space-y-5">
            <SectionTitle icon={User} title="Basics" />
            <Field label="Full name" value={bank.name} onChange={(v) => set({ name: v })} />
            <div className="grid sm:grid-cols-3 gap-3">
              <Field label="Email" value={bank.contact.email} onChange={(v) => set({ contact: { ...bank.contact, email: v } })} />
              <Field label="Phone" value={bank.contact.phone} onChange={(v) => set({ contact: { ...bank.contact, phone: v } })} />
              <Field label="Location" value={bank.contact.location} onChange={(v) => set({ contact: { ...bank.contact, location: v } })} />
            </div>
            <Field
              label="Links (comma separated)"
              value={bank.contact.links.join(', ')}
              onChange={(v) => set({ contact: { ...bank.contact, links: splitList(v) } })}
            />
            <div>
              <label className="label">Summary</label>
              <textarea className="input min-h-[90px]" value={bank.summary} onChange={(e) => set({ summary: e.target.value })} />
            </div>
          </section>

          <section className="panel space-y-5">
            <SectionTitle icon={Wrench} title="Skills" />
            {Object.entries(bank.skills).map(([category, items]) => (
              <div key={category} className="flex flex-col sm:flex-row gap-2 sm:items-end rounded-xl border border-slate-200 sm:border-0 bg-slate-50/60 sm:bg-transparent p-3 sm:p-0">
                <div className="sm:w-1/3">
                  <label className="label">Category</label>
                  <input
                    className="input"
                    defaultValue={category}
                    onBlur={(e) => {
                      const name = e.target.value.trim();
                      if (!name || name === category) return;
                      // rename while keeping the order
                      set({ skills: Object.fromEntries(Object.entries(bank.skills).map(([k, v]) => [k === category ? name : k, v])) });
                    }}
                  />
                </div>
                <div className="flex-1">
                  <label className="label">Items (comma separated)</label>
                  <input
                    className="input"
                    defaultValue={items.join(', ')}
                    onBlur={(e) => set({ skills: { ...bank.skills, [category]: splitList(e.target.value) } })}
                  />
                </div>
                <button
                  className="self-end sm:self-auto p-2.5 sm:p-2 text-slate-400 hover:text-red-600 active:text-red-600"
                  aria-label="Remove category"
                  onClick={() => set({ skills: Object.fromEntries(Object.entries(bank.skills).filter(([k]) => k !== category)) })}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            <button
              className="btn-outline"
              onClick={() => set({ skills: { ...bank.skills, [`Category ${Object.keys(bank.skills).length + 1}`]: [] } })}
            >
              <Plus size={16} /> Add category
            </button>
          </section>

          <section className="space-y-5">
            <SectionTitle icon={Briefcase} title="Experience" />
            {bank.experiences.map((exp, i) => (
              <div key={i} className="panel space-y-5">
                <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-amber-600">Job {i + 1}</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Field label="Job title" value={exp.title} onChange={(v) => setExp(i, { title: v })} />
                  <Field label="Company" value={exp.company} onChange={(v) => setExp(i, { company: v })} />
                  <Field label="Location" value={exp.location} onChange={(v) => setExp(i, { location: v })} />
                  <Field label="Dates" value={exp.dates} onChange={(v) => setExp(i, { dates: v })} />
                  <Field label="Short id (a-z, 0-9, _)" value={exp.id} onChange={(v) => setExp(i, { id: v.toLowerCase().replace(/[^a-z0-9_]/g, '') })} />
                  <div>
                    <label className="label">Bullets shown on resume</label>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      max={15}
                      value={exp.max_bullets}
                      onChange={(e) => setExp(i, { max_bullets: Math.min(15, Math.max(1, Number(e.target.value) || 1)) })}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="label">Bullets (all of them; the AI picks the best ones per job)</label>
                  {exp.bullets.map((b, k) => (
                    <div key={k} className="flex gap-2">
                      <textarea
                        className="input min-h-[60px]"
                        value={b}
                        onChange={(e) => setExp(i, { bullets: exp.bullets.map((x, j) => (j === k ? e.target.value : x)) })}
                      />
                      <button
                        className="p-2.5 sm:p-2 text-slate-400 hover:text-red-600 active:text-red-600 self-start"
                        aria-label="Remove bullet"
                        disabled={exp.bullets.length === 1}
                        onClick={() => setExp(i, { bullets: exp.bullets.filter((_, j) => j !== k) })}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                  <button className="btn-outline" onClick={() => setExp(i, { bullets: [...exp.bullets, ''] })}>
                    <Plus size={16} /> Add bullet
                  </button>
                </div>
                {bank.experiences.length > 1 && (
                  <button className="text-sm text-red-600 hover:underline" onClick={() => set({ experiences: bank.experiences.filter((_, j) => j !== i) })}>
                    Remove this job
                  </button>
                )}
              </div>
            ))}
            <button className="btn-outline" onClick={() => set({ experiences: [...bank.experiences, emptyExperience(bank.experiences.length + 1)] })}>
              <Plus size={16} /> Add job
            </button>
          </section>

          <section className="space-y-5">
            <SectionTitle icon={GraduationCap} title="Education" />
            {bank.education.map((ed, i) => (
              <div key={i} className="panel space-y-5">
                <div className="grid sm:grid-cols-3 gap-3">
                  <Field label="Degree" value={ed.degree} onChange={(v) => setEdu(i, { degree: v })} />
                  <Field label="School" value={ed.school} onChange={(v) => setEdu(i, { school: v })} />
                  <Field label="Date" value={ed.date} onChange={(v) => setEdu(i, { date: v })} />
                </div>
                <Field label="Details (optional)" value={ed.details} onChange={(v) => setEdu(i, { details: v })} />
                <button className="text-sm text-red-600 hover:underline" onClick={() => set({ education: bank.education.filter((_, j) => j !== i) })}>
                  Remove
                </button>
              </div>
            ))}
            <button className="btn-outline" onClick={() => set({ education: [...bank.education, { degree: '', school: '', date: '', details: '' }] })}>
              <Plus size={16} /> Add education
            </button>
          </section>

          <div className="sticky bottom-[calc(4.75rem+env(safe-area-inset-bottom))] md:bottom-4 z-30 flex justify-end rounded-2xl bg-white border border-slate-300 shadow-[0_12px_32px_-12px_rgba(15,23,42,0.35)] px-4 sm:px-5 py-3">
            <button className="btn-primary w-full sm:w-auto" onClick={save} disabled={saving}>
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {draft ? 'Save imported career bank' : 'Save'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="label">{label}</label>
      <input className="input" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="icon-chip">
        <Icon size={18} />
      </div>
      <h2 className="text-lg font-bold">{title}</h2>
    </div>
  );
}
