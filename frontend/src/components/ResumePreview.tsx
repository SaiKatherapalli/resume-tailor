import type { CareerBank, TailorResult } from '../types';

/** Shows the tailored resume. Header, job titles and education are copied from the career bank, as in the LaTeX. */
export default function ResumePreview({ bank, resume }: { bank: CareerBank | null; resume: TailorResult['resume'] }) {
  const byId = new Map(bank?.experiences.map((e) => [e.id, e]));
  const contact = bank?.contact;

  return (
    <div
      id="resume-print"
      className="bg-white border border-slate-300 shadow-[0_24px_48px_-24px_rgba(15,23,42,0.3)] rounded-lg p-5 sm:p-10 text-[12.5px] sm:text-[13px] leading-relaxed font-serif text-slate-900 print:border-0 print:shadow-none print:rounded-none print:p-0 print:text-[10.5pt] print:leading-snug"
    >
      {bank && (
        <header className="text-center mb-4">
          <h2 className="text-2xl font-bold tracking-wide print:text-[20pt]">{bank.name}</h2>
          <p className="text-slate-600">
            {[contact?.email, contact?.phone, contact?.location, ...(contact?.links ?? [])].filter(Boolean).join('  |  ')}
          </p>
        </header>
      )}

      <Section title="Summary">
        <p className="text-justify [hyphens:auto]">{resume.summary}</p>
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
            <div key={exp.experience_id} className="mb-3 break-inside-avoid-page">
              <div className="flex flex-col sm:flex-row sm:justify-between sm:gap-4 print:flex-row print:justify-between print:gap-4">
                <b>{meta ? `${meta.title}, ${meta.company}` : exp.experience_id}</b>
                <span className="text-slate-600 sm:whitespace-nowrap print:whitespace-nowrap">{meta?.dates}</span>
              </div>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                {exp.bullets.map((b, i) => (
                  <li key={i} className="break-inside-avoid text-justify [hyphens:auto]" title={`Based on: ${b.source_ids.join(', ')}`}>
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
            <div key={i} className="flex flex-col sm:flex-row sm:justify-between sm:gap-4 print:flex-row print:justify-between print:gap-4">
              <span>
                <b>{ed.degree}</b>, {ed.school}
              </span>
              <span className="text-slate-600 sm:whitespace-nowrap print:whitespace-nowrap">{ed.date}</span>
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
