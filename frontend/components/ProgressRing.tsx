// Real animated SVG arc, not a plain circle+text — DESIGN.md calls for an
// "animated SVG circular progress indicator." The dashoffset transition is
// what makes it animate when `value` changes (e.g. after marking a step done).
export default function ProgressRing({ value, total }: { value: number; total: number }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const pct = total > 0 ? value / total : 0;
  const offset = circumference * (1 - pct);

  return (
    <div className="relative flex h-20 w-20 shrink-0 items-center justify-center">
      <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80" aria-hidden="true">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="#DBEAFE" strokeWidth="8" />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="#1D4ED8"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="absolute text-lg font-semibold text-blue-800">
        {total > 0 ? `${value}/${total}` : "–"}
      </span>
    </div>
  );
}
