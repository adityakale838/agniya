import Link from 'next/link';
import type { ReactNode } from 'react';

/** The AGNIYA wordmark: report-header capitals at Archivo's widest. */
export function Wordmark({ className = '' }: { className?: string }) {
  return <span className={`wide font-extrabold tracking-[-0.01em] ${className}`}>AGNIYA</span>;
}

/** A message field tag, as on an interbank slip (":32A:"). */
export function Tag({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`tag ${className}`}>{children}</span>;
}

/** Top strip of a sheet: wordmark left, links right, a perforation under it. */
export function SheetHeader({ children }: { children?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 bg-paper">
      <div className="mx-auto flex h-16 max-w-[1320px] items-center gap-6 px-5 md:px-10">
        <Link href="/" className="text-[1.35rem] text-ink" aria-label="AGNIYA home">
          <Wordmark />
        </Link>
        <div className="ml-auto flex items-center gap-1 md:gap-2">{children}</div>
      </div>
      <div className="perf h-px" aria-hidden />
    </header>
  );
}

/** Ink button and its quieter sibling. Square, like everything printed. */
export const inkButton =
  'inline-flex h-11 items-center gap-2 bg-ink px-5 text-[0.95rem] font-semibold text-paper transition-[transform,background-color] hover:bg-[#2c332f] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45';
export const paperButton =
  'inline-flex h-11 items-center gap-2 border border-ink/70 px-5 text-[0.95rem] font-semibold text-ink transition-[transform,background-color] hover:bg-band active:translate-y-px disabled:cursor-not-allowed disabled:opacity-45';
export const navLink = 'hidden px-3 py-2 text-[0.9rem] font-medium text-ink-2 hover:text-ink lg:inline-block';

/** A sheet of fanfold stock: tractor holes down both edges. */
export function Sheet({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className="relative bg-card">
      <div className="tractor absolute inset-y-0 left-0 w-4 border-r border-dashed border-band-line [--hole:3px] md:w-7 md:[--hole:5px]" aria-hidden />
      <div className="tractor absolute inset-y-0 right-0 w-4 border-l border-dashed border-band-line [--hole:3px] md:w-7 md:[--hole:5px]" aria-hidden />
      <div className={`px-4 md:px-7 ${className}`}>{children}</div>
    </div>
  );
}
