import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { LiveSlip } from '@/components/live-slip';
import { Sheet, SheetHeader, Tag, Wordmark, inkButton, navLink, paperButton } from '@/components/paper';

const REPO = 'https://github.com/adityakale838/agniya';

const PIPELINE = [
  { name: 'Encode and pack', side: 'Bank', text: 'Decimals become exact integers. 48 to 73 values share one 2048-bit plaintext, with room so totals never overflow.' },
  { name: 'Encrypt and tag', side: 'Bank', text: 'Paillier encryption, an integrity tag inside every plaintext, order tags only on columns used for range filters.' },
  { name: 'Upload and store', side: 'Server', text: 'The server keeps ciphertexts and tags. It never receives a key, a plaintext value or a group label.' },
  { name: 'Compute blind', side: 'Server', text: 'Multiplying ciphertexts adds the values inside them. A GROUP BY is one product and one decryption.' },
  { name: 'Decrypt and verify', side: 'Bank', text: 'Only totals are decrypted. A wrong, partial or replayed answer fails its integrity check and raises an error.' },
];

const MEASURED = [
  { what: 'Encrypt one value', where: '1,000,000 values in 6.39 s, all cores', figure: '6.4 µs' },
  { what: 'SUM over a million encrypted values', where: 'exact, one decryption', figure: '130 ms' },
  { what: 'SUM over ten million values', where: 'encrypting them took 57.3 s', figure: '1.32 s' },
  { what: 'Storage per value', where: 'values packed into ciphertexts', figure: '7-11 B' },
  { what: 'GROUP BY region, 1,338 rows', where: 'keys held by the client', figure: '3.9 ms' },
];

const SEAL = [
  { row: 'Encrypt, per value (one-time)', agniya: '6.4 µs', seal: '1.1 µs', lead: 'seal' },
  { row: 'SUM GROUP BY region, 1,338 rows', agniya: '4.0 ms', seal: '478 ms', lead: 'agniya' },
  { row: 'Storage per value', agniya: '7-11 bytes', seal: '53 bytes at best', lead: 'agniya' },
  { row: 'Same totals', agniya: 'Yes', seal: 'Yes, identical', lead: '' },
  { row: 'Post-quantum', agniya: 'No', seal: 'Yes', lead: 'seal' },
  { row: 'Filters, GROUP BY, statistics, checks', agniya: 'Built in', seal: 'Would need building', lead: 'agniya' },
];

const QUESTIONS = [
  { title: 'Loan exposure by risk band', sql: 'SUM(loan_amount) GROUP BY risk_band', time: '0.2 s' },
  { title: 'Default rate by segment', sql: 'AVG(default_flag) GROUP BY segment', time: '0.2 s' },
  { title: 'Median balance by region', sql: 'MEDIAN(balance) GROUP BY region', time: '0.2 s' },
  { title: 'Spend volatility by segment', sql: 'STDDEV(monthly_spend) GROUP BY segment', time: '0.3 s' },
  { title: 'Sub-prime exposure by product', sql: 'SUM(loan_amount) WHERE credit_score BETWEEN 300 AND 600 GROUP BY product', time: '0.3 s' },
  { title: 'Exposure by region and segment', sql: 'SUM(loan_amount) GROUP BY region, segment', time: '0.4 s' },
];

function Tear() {
  return <div className="perf my-0 h-px" aria-hidden />;
}

export default function Home() {
  return (
    <div className="min-h-[100dvh] bg-paper text-ink">
      <SheetHeader>
        <a href="#pipeline" className={navLink}>How it works</a>
        <a href="#numbers" className={navLink}>Numbers</a>
        <a href="#questions" className={navLink}>Bank questions</a>
        <a href="#limits" className={navLink}>Limits</a>
        <a href={REPO} className={navLink}>GitHub</a>
        <span className="hidden sm:block"><Link href="/dashboard" className={`${inkButton} h-10 px-4`}>Open the dashboard</Link></span>
      </SheetHeader>

      <main className="mx-auto max-w-[1320px] md:px-6">
        <Sheet>
          {/* First viewport: the offer beside the mechanism working. */}
          <section className="grid items-center gap-10 px-5 pb-16 pt-12 md:px-10 lg:grid-cols-[1.02fr_1fr] lg:gap-14 lg:pb-20 lg:pt-16">
            <div className="max-w-[38rem]">
              <h1 className="wide text-balance text-[clamp(2.2rem,3.7vw,3.5rem)] font-extrabold leading-[1.02] tracking-[-0.02em]">
                Run the bank&apos;s numbers on data no one else can read.
              </h1>
              <p className="mt-6 max-w-[30rem] text-[1.15rem] leading-relaxed text-ink-2">
                Exact SUM, AVG, MEDIAN and GROUP BY on customer data that stays encrypted. The server never holds a key.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link href="/dashboard" className={inkButton}>
                  Open the dashboard <ArrowRight className="size-4" strokeWidth={2.2} />
                </Link>
                <a href="#numbers" className={paperButton}>See the numbers</a>
              </div>
            </div>
            <LiveSlip />
          </section>

          <Tear />

          {/* The pipeline as a message route: who holds what at each step. */}
          <section id="pipeline" className="scroll-mt-20 px-5 py-16 md:px-10 lg:py-20">
            <h2 className="wide max-w-[40rem] text-[clamp(1.7rem,2.6vw,2.4rem)] font-bold leading-[1.08] tracking-[-0.015em]">
              Five steps from a bank table to a checked answer
            </h2>
            <p className="mt-4 max-w-[38rem] text-[1.05rem] leading-relaxed text-ink-2">
              Three happen inside the bank, two on a server that holds no key. The same steps run in the Python client or in the dashboard&apos;s browser tab.
            </p>
            <ol className="mt-12 grid gap-px border border-band-line bg-band-line md:grid-cols-5">
              {PIPELINE.map((s, i) => (
                <li key={s.name} className={`flex flex-col gap-4 p-5 ${s.side === 'Server' ? 'bg-band' : 'bg-card'}`}>
                  <div className="flex items-baseline justify-between">
                    <span className="font-mono text-[1.6rem] font-semibold leading-none text-ink">{i + 1}</span>
                    <Tag className={s.side === 'Server' ? 'text-ink' : ''}>{s.side === 'Server' ? 'server, no key' : 'bank'}</Tag>
                  </div>
                  <h3 className="semi-wide text-[1.08rem] font-bold leading-snug">{s.name}</h3>
                  <p className="text-[0.95rem] leading-relaxed text-ink-2">{s.text}</p>
                </li>
              ))}
            </ol>
          </section>

          <Tear />

          {/* Measured numbers as a printed run report, figures in the right-hand column. */}
          <section id="numbers" className="scroll-mt-20 px-5 py-16 md:px-10 lg:py-20">
            <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
              <div>
                <h2 className="wide text-[clamp(1.7rem,2.6vw,2.4rem)] font-bold leading-[1.08] tracking-[-0.015em]">
                  Measured, every result checked exact
                </h2>
                <p className="mt-4 max-w-[30rem] text-[1.05rem] leading-relaxed text-ink-2">
                  One laptop: Intel i5-1145G7, 16 GB, 2048-bit keys, on AC power. Every figure comes from one benchmark script that checks each answer against plaintext.
                </p>
                <p className="mt-6 text-[1.05rem] leading-relaxed">
                  <span className="font-mono font-semibold">10.3×</span> faster than our own first honest baseline on the same machine.
                </p>
              </div>
              <dl className="border-t border-ink">
                {MEASURED.map((m, i) => (
                  <div key={m.what} className={`grid grid-cols-[1fr_auto] items-baseline gap-x-6 gap-y-1 border-b border-band-line px-1 py-4 ${i % 2 ? '' : 'bg-band'}`}>
                    <dt className="text-[1.02rem] font-semibold">{m.what}</dt>
                    <dd className="row-span-2 self-center text-right font-mono text-[clamp(1.5rem,2.4vw,2.1rem)] font-semibold tracking-[-0.02em]">{m.figure}</dd>
                    <dd className="text-[0.9rem] text-ink-2">{m.where}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>

          <Tear />

          {/* The SEAL comparison, both directions shown. */}
          <section className="px-5 py-16 md:px-10 lg:py-20">
            <h2 className="wide max-w-[44rem] text-[clamp(1.7rem,2.6vw,2.4rem)] font-bold leading-[1.08] tracking-[-0.015em]">
              Against Microsoft SEAL, on the same laptop
            </h2>
            <p className="mt-4 max-w-[42rem] text-[1.05rem] leading-relaxed text-ink-2">
              SEAL is a general lattice library. It computes the same SUM and GROUP BY totals, identically, which is our independent check. It encrypts faster; we answer queries faster and store less.
            </p>
            <div className="mt-10 overflow-x-auto">
              <table className="w-full min-w-[620px] border-collapse text-left">
                <thead>
                  <tr className="border-b-2 border-ink">
                    <th className="w-[44%] py-3 pr-4 text-[0.85rem] font-medium text-ink-2" scope="col"><span className="sr-only">Measure</span></th>
                    <th className="py-3 pr-4 font-mono text-[0.95rem] font-semibold" scope="col">AGNIYA (Paillier)</th>
                    <th className="py-3 font-mono text-[0.95rem] font-semibold" scope="col">Microsoft SEAL (BFV)</th>
                  </tr>
                </thead>
                <tbody>
                  {SEAL.map(r => (
                    <tr key={r.row} className="border-b border-band-line">
                      <th scope="row" className="py-4 pr-4 text-[1rem] font-medium">{r.row}</th>
                      <td className={`py-4 pr-4 font-mono text-[1.05rem] ${r.lead === 'agniya' ? 'font-bold text-ink' : 'text-ink-2'}`}>{r.agniya}</td>
                      <td className={`py-4 font-mono text-[1.05rem] ${r.lead === 'seal' ? 'font-bold text-ink' : 'text-ink-2'}`}>{r.seal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-6 text-[1.05rem]">
              SEAL encrypts about <b>6× faster</b>. AGNIYA answers queries about <b>120× faster</b> and stores data about <b>5× smaller</b>.
            </p>
          </section>

          <Tear />

          {/* Bank questions as one banded printout listing. */}
          <section id="questions" className="scroll-mt-20 px-5 py-16 md:px-10 lg:py-20">
            <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:gap-14">
              <div>
                <h2 className="wide text-[clamp(1.7rem,2.6vw,2.4rem)] font-bold leading-[1.08] tracking-[-0.015em]">
                  Questions a bank asks, answered encrypted
                </h2>
                <p className="mt-4 max-w-[28rem] text-[1.05rem] leading-relaxed text-ink-2">
                  2,000 synthetic customers, encrypted in the browser in 3.5 s. Each question is one click in the dashboard; every answer matched a plaintext computation exactly.
                </p>
                <Link href="/dashboard" className={`${inkButton} mt-8`}>
                  Try them in the dashboard <ArrowRight className="size-4" strokeWidth={2.2} />
                </Link>
              </div>
              <div>
                <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2">
                  <Tag>question and the encrypted query behind it</Tag>
                  <Tag>repeat run</Tag>
                </div>
                <ul>
                  {QUESTIONS.map((q, i) => (
                    <li key={q.title} className={`grid grid-cols-[1fr_auto] items-center gap-x-6 px-1 py-4 ${i % 2 ? '' : 'bg-band'}`}>
                      <div>
                        <div className="text-[1.05rem] font-semibold leading-snug">{q.title}</div>
                        <code className="mt-1 block font-mono text-[0.78rem] leading-relaxed text-ink-2">{q.sql}</code>
                      </div>
                      <span className="font-mono text-[1.3rem] font-semibold">{q.time}</span>
                    </li>
                  ))}
                </ul>
                <div className="perf h-px" aria-hidden />
              </div>
            </div>
          </section>

          <Tear />

          {/* What the server can and cannot see, and the limits not yet closed. */}
          <section id="limits" className="scroll-mt-20 px-5 py-16 md:px-10 lg:py-20">
            <h2 className="wide max-w-[44rem] text-[clamp(1.7rem,2.6vw,2.4rem)] font-bold leading-[1.08] tracking-[-0.015em]">
              What the server sees, and what it never does
            </h2>
            <div className="mt-10 grid gap-10 md:grid-cols-2">
              <div>
                <h3 className="semi-wide text-[1.1rem] font-bold">It never receives</h3>
                <ul className="mt-4 space-y-3 text-[1.02rem]">
                  <li>The private key, the order keys or the integrity keys</li>
                  <li>Any customer value, decimal or label</li>
                  <li>The GROUP BY labels; they stay with the bank</li>
                  <li>A way to change an answer without the bank noticing</li>
                </ul>
              </div>
              <div>
                <h3 className="semi-wide text-[1.1rem] font-bold">It does see</h3>
                <ul className="mt-4 space-y-3 text-[1.02rem] text-ink-2">
                  <li>Row counts and ciphertext sizes</li>
                  <li>The order of values in columns marked for range filters</li>
                  <li>Which stored ciphertexts a median query reads</li>
                </ul>
              </div>
            </div>
            <div className="mt-12 border-y-2 border-ink py-5">
              <p className="text-[1.02rem] leading-relaxed">
                <span className="font-semibold">Limits today.</span>{' '}
                2048-bit keys give about 112-bit security. Paillier is not post-quantum. No independent security review has been done yet.
              </p>
            </div>
          </section>

          <Tear />

          {/* Close: the ask. */}
          <section className="px-5 pb-14 pt-16 md:px-10 lg:pt-20">
            <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
              <div>
                <h2 className="wide text-[clamp(1.9rem,3.2vw,3rem)] font-extrabold leading-[1.04] tracking-[-0.02em]">
                  One reporting use case. Six weeks. Results that must match exactly.
                </h2>
                <p className="mt-5 max-w-[36rem] text-[1.05rem] leading-relaxed text-ink-2">
                  Weeks 1-2 reproduce three to five existing reports on synthetic or masked data. Weeks 3-4 connect one real pipeline with keys in a test KMS. Weeks 5-6 bring a security review and a rollout decision.
                </p>
              </div>
              <div className="flex flex-wrap gap-3 lg:justify-end">
                <Link href="/dashboard" className={inkButton}>
                  Open the dashboard <ArrowRight className="size-4" strokeWidth={2.2} />
                </Link>
                <a href={REPO} className={paperButton}>Read the code</a>
              </div>
            </div>
          </section>
        </Sheet>

        <footer className="flex flex-col gap-2 px-5 py-8 text-[0.88rem] text-ink-2 md:flex-row md:items-center md:justify-between md:px-10">
          <span><Wordmark className="text-ink" /> &nbsp;CSE DS B, Vishwakarma Institute of Technology, Pune</span>
          <span>Apache License 2.0 · 319 automated tests on every change</span>
        </footer>
      </main>
    </div>
  );
}
