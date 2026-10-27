export default function Footer() {
  return (
    <footer className="w-full bg-gradient-to-br from-slate-900 to-slate-800 text-slate-300 mt-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row justify-between gap-2 text-xs">
        <p>
          <span className="text-white font-semibold">ResumeTailor</span>: your resume, rewritten for each job. Only
          facts from your own career history.
        </p>
        <p className="text-slate-400">© {new Date().getFullYear()} ResumeTailor</p>
      </div>
    </footer>
  );
}
