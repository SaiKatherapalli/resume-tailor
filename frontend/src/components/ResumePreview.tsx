import type { CareerBank, CustomSection, TailorResult } from '../types';

/** Shows the tailored resume. Header, job titles, education and extra sections (projects, certifications...) are copied from the career bank, as in the LaTeX. */
export default function ResumePreview({ bank, resume }: { bank: CareerBank | null; resume: TailorResult['resume'] }) {
  const byId = new Map(bank?.experiences.map((e) => [e.id, e]));
  const contact = bank?.contact;
  const extraSections = (bank?.sections ?? []).filter((sec) => sec.entries.length > 0);

  return (
    <div
      id="resume-print"
      className="bg-white border border-slate-300 shadow-[0_24px_48px_-24px_rgba(15,23,42,0.3)] rounded-lg p-5 sm:p-10 text-[12.5px] sm:text-[13px] leading-relaxed font-serif text-slate-900 print:border-0 print:shadow-none print:rounded-none print:p-0 print:text-[10.5pt] print:leading-snug"
    >
      {bank && (
        <header className="text-center mb-4">
          <h2 className="text-2xl font-bold tracking-wide print:text-[20pt]">{bank.name}</h2>
          <p className="text-slate-600">
            {[
              contact?.email,
              contact?.phone,
              contact?.location,
              ...(contact?.links ?? []).filter((l) => l.label).map((l) => (l.url ? `[${l.label}](${l.url})` : l.label)),
            ]
              .filter(Boolean)
              .map((part, i) => (
                <span key={i}>
                  {i > 0 && '  |  '}
                  {linkify(part as string)}
                </span>
              ))}
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

      {extraSections.filter((sec) => !sec.after_education).map(renderExtra)}

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

      {extraSections.filter((sec) => sec.after_education).map(renderExtra)}
    </div>
  );
}

function renderExtra(sec: CustomSection, i: number) {
  return (
    <Section key={`${sec.title}-${i}`} title={sec.title}>
      {sec.entries.map((entry, k) => (
        <div key={k} className="mb-2 break-inside-avoid-page">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:gap-4 print:flex-row print:justify-between print:gap-4">
            <b>{linkify(entry.heading)}</b>
            <span className="text-slate-600 sm:whitespace-nowrap print:whitespace-nowrap">{entry.date}</span>
          </div>
          {entry.subtitle && <p>{linkify(entry.subtitle)}</p>}
          {entry.bullets.length > 0 && (
            <ul className="list-disc pl-5 mt-1 space-y-0.5">
              {entry.bullets.map((b, j) => (
                <li key={j} className="break-inside-avoid text-justify [hyphens:auto]">
                  {linkify(b)}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </Section>
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

/** "[Live Demo](https://x.app)" becomes a link; everything else stays plain text. */
function linkify(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    parts.push(text.slice(last, m.index));
    parts.push(
      <a key={m.index} href={m[2]} target="_blank" rel="noopener noreferrer" className="underline">
        {m[1]}
      </a>,
    );
    last = m.index! + m[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}
