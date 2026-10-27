import { motion } from 'framer-motion';

interface Props {
  eyebrow: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  center?: boolean;
}

export default function PageHeader({ eyebrow, title, subtitle, action, center }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={center ? 'text-center' : 'flex flex-wrap items-end justify-between gap-4 pb-7 border-b border-slate-200'}
    >
      <div>
        <div className={`flex items-center gap-3 ${center ? 'justify-center' : ''}`}>
          <span className="h-px w-8 bg-amber-500" />
          <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-amber-600">{eyebrow}</span>
          {center && <span className="h-px w-8 bg-amber-500" />}
        </div>
        {title && (
          <h1 className="mt-3 text-[28px] sm:text-[32px] leading-tight font-bold tracking-tight text-slate-900">{title}</h1>
        )}
        {subtitle && <p className={`mt-3 text-[15px] text-slate-500 max-w-2xl leading-relaxed ${center ? 'mx-auto' : ''}`}>{subtitle}</p>}
      </div>
      {action}
    </motion.div>
  );
}
