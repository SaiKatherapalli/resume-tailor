import { motion } from 'framer-motion';
import { ArrowRight, Database, FileDown, ShieldCheck, Sparkles } from 'lucide-react';

const steps = [
  {
    icon: Database,
    title: 'Build your career bank',
    text: 'Upload your resume once. Check and edit every fact. This is the only source the AI may use.',
  },
  {
    icon: Sparkles,
    title: 'Paste a job description',
    text: 'The AI finds the keywords, picks your best-matching bullets and rewrites them for that job.',
  },
  {
    icon: ShieldCheck,
    title: 'Every bullet is checked',
    text: 'Invented numbers, skills and wrong sources are caught and sent back for a fix.',
  },
  {
    icon: FileDown,
    title: 'Download LaTeX or PDF',
    text: 'A clean, ATS-friendly resume, ready to send.',
  },
];

export default function Landing({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="py-10 sm:py-16">
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="text-center max-w-3xl mx-auto">
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase bg-amber-100 text-amber-700">
          AI resume tailoring
        </span>
        <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight">
          One resume. <span className="text-amber-500">Tailored</span> to every job.
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Paste a job description and get your resume rewritten for it, using only the facts from your own career history.
        </p>
        <button onClick={onGetStarted} className="btn-primary mt-8 !px-6 !py-3 text-base">
          Get started <ArrowRight size={18} />
        </button>
      </motion.div>

      <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <motion.div
            key={s.title}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className="card"
          >
            <div className="w-10 h-10 rounded-lg bg-slate-900 text-amber-400 flex items-center justify-center">
              <s.icon size={20} />
            </div>
            <h3 className="mt-3 font-semibold">{s.title}</h3>
            <p className="mt-1 text-sm text-slate-600">{s.text}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
