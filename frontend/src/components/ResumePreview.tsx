import type { CareerBank, TailorResult } from '../types';

/** Shows the tailored resume. Header, job titles and education are copied from the career bank, as in the LaTeX. */
export default function ResumePreview({ bank, resume }: { bank: CareerBank | null; resume: TailorResult['resume'] }) {
  const byId = new Map(bank?.experiences.map((e) => [e.id, e]));
  const contact = bank?.contact;

  return (
    <div className="bg-white border border-slate-200 shadow rounded-lg p-8 text-[13px] leading-relaxed font-serif text-slate-900">
      {bank && (
        <header className="text-center mb-4">
          <h2 className="text-2xl font-bold tracking-wide">{bank.name}</h2>
          <p className="text-slate-600">
            {[contact?.email, contact?.phone, contact?.location, ...(contact?.links ?? [])].filter(Boolean).join('  |  ')}
          </p>
        </header>
      )}

      <Section title="Summary">
        <p>{resume.summary}</p>
      </Section>

      <Section title="Skills">
        {resume.skills.map((row) => (
          <p key={row.category}>
            <b>{row.category}:</b> {row.items.join(', ')}
          </p>
        ))}
      </Section>

      <Section title="Experience">
        {resume.experiences.map((exp) => {
          const meta = byId.get(exp.experience_id);
          return (
            <div key={exp.experience_id} className="mb-3">
              <div className="flex justify-between gap-4">
                <b>{meta ? `${meta.title}, ${meta.company}` : exp.experience_id}</b>
                <span className="text-slate-600 whitespace-nowrap">{meta?.dates}</span>
              </div>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                {exp.bullets.map((b, i) => (
                  <li key={i} title={`Based on: ${b.source_ids.join(', ')}`}>
                    {b.text}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </Section>

      {bank && bank.education.length > 0 && (
        <Section title="Education">
          {bank.education.map((ed, i) => (
            <div key={i} className="flex justify-between gap-4">
              <span>
                <b>{ed.degree}</b>, {ed.school}
              </span>
              <span className="text-slate-600 whitespace-nowrap">{ed.date}</span>
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-3">
      <h3 className="text-sm font-bold uppercase tracking-wider border-b border-slate-400 mb-1.5">{title}</h3>
      {children}
    </section>
  );
}
