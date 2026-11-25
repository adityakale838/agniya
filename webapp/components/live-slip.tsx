'use client';

import { useCallback, useEffect, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { decrypt, encrypt, keypairFromPrimes } from '@/lib/agniya-browser';
import { Tag } from '@/components/paper';

// A demo key, published here on purpose so the page can show real Paillier ciphertexts without waiting
// for key generation. The dashboard makes a fresh key for every dataset and never shows it.
const P = BigInt('0xf5b25e9ec4b4bd952c5a6704be45018874d5b19cc625a4c6dfa5e6b1edce1256c509e53f4dfd5627b709abe7a9d1edd01bbf74908f7cf26789fe2faac87a99c508979c721f11c78ffe88ecac47af4a9db5492f1dba75f1b547f9a1d02df7635854f6aca032b9c5fe024c59389855a06bb8d23fc0edfc1f0dabab14c8f14bf1a7');
const Q = BigInt('0xfec34c1cffdfb372d876e0e9e6d702326f3701fed364710b45441dee70fa63029a5de92560f6ba295e00aa0dfed2720aaa7c6660f5a39f470fcf335d4377b47e4e119d8157ef93f47d8ca97338f224a1d57f0734f49b948bf9fb1a3c514a891c52c5866241563c02c1d38af125a17089d5f1e90de983890f31de2ade97e68ee3');

/** Three synthetic customers (no real data): loan amounts in fixed point, 2 decimals. */
const ROWS = [
  { id: 'C100231', amount: 1245000n },
  { id: 'C100877', amount: 3907150n },
  { id: 'C101402', amount: 518625n },
];
/** One printed line: alternate green bands, full width of the slip. */
const line = (i: number) => `feed-line px-5 md:px-6 ${i % 2 ? '' : 'bg-band'}`;
const money = (v: bigint) => (Number(v) / 100).toLocaleString('en-GB', { minimumFractionDigits: 2 });

interface Print { cts: string[]; product: string; total: bigint; ms: number }

export function LiveSlip() {
  const [key] = useState(() => keypairFromPrimes(P, Q));
  const [print, setPrint] = useState<Print | null>(null);
  const [run, setRun] = useState(0);

  const printOnce = useCallback(() => {
    const { pub, priv } = key;
    const t0 = performance.now();
    const cs = ROWS.map(r => encrypt(pub, priv, r.amount));
    const product = cs.reduce((a, c) => (a * c) % pub.nSquared, 1n);
    const total = decrypt(priv, product);
    setPrint({ cts: cs.map(c => c.toString(16)), product: product.toString(16), total, ms: performance.now() - t0 });
    setRun(n => n + 1);
  }, [key]);

  useEffect(() => {
    const id = setTimeout(printOnce, 60);  // after first paint: three 2048-bit encryptions take a moment
    return () => clearTimeout(id);
  }, [printOnce]);

  const expected = ROWS.reduce((s, r) => s + r.amount, 0n);
  const ok = print?.total === expected;

  return (
    <figure className="relative border border-band-line bg-[#fbfcf8] shadow-[0_18px_40px_-24px_rgba(27,31,29,0.45)]" aria-label="Live encryption demo">
      {/* Each printed line owns its band: green, paper, green... like the fanfold it imitates. */}
      <div key={run}>
        <div className={`${line(0)} flex items-baseline justify-between gap-3 py-3`} style={{ ['--i' as string]: 0 }}>
          <span className="font-mono text-[0.78rem] font-semibold text-ink">SUM(loan_amount)</span>
          <Tag>3 synthetic customers</Tag>
        </div>

        {ROWS.map((r, i) => (
          <div key={r.id} className={`${line(i + 1)} grid grid-cols-[auto_1fr] gap-x-4 py-2.5`} style={{ ['--i' as string]: i + 1 }}>
            <div className="w-[7.5rem]">
              <Tag>:61: {r.id}</Tag>
              <div className="font-mono text-[0.95rem] text-ink">{money(r.amount)}</div>
            </div>
            <div className="cipher h-[39px] overflow-hidden" aria-label={`Ciphertext of row ${i + 1}`}>
              {print ? print.cts[i] : 'encrypting…'}
            </div>
          </div>
        ))}

        <div className={`${line(4)} py-3`} style={{ ['--i' as string]: 4 }}>
          <Tag>:32A: server multiplies them, holding no key</Tag>
          <div className="cipher mt-1 h-[26px] overflow-hidden">{print ? print.product : ''}</div>
        </div>

        <div className={`${line(5)} flex flex-wrap items-end justify-between gap-3 py-3`} style={{ ['--i' as string]: 5 }}>
          <div>
            <Tag>:79: bank decrypts once</Tag>
            <div className="font-mono text-[1.7rem] font-semibold leading-tight text-ink">
              {print ? money(print.total) : '…'}
            </div>
          </div>
          {print && (
            <span className={`stamp ${ok ? 'text-ok' : 'text-ribbon'}`}>{ok ? 'checked: equals the sum' : 'mismatch'}</span>
          )}
        </div>
      </div>
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-t border-band-line px-5 py-3 text-[0.82rem] text-ink-2 md:px-6">
        <span>
          Real 2048-bit Paillier ciphertexts, made in this browser
          {print ? ` in ${Math.round(print.ms)} ms` : ''}. Each is 1,024 hex digits; shown cut.
        </span>
        <button type="button" onClick={printOnce}
                className="inline-flex items-center gap-1.5 font-semibold text-ink underline decoration-ink/30 hover:decoration-ink">
          <RotateCcw className="size-3.5" strokeWidth={2} /> Print again: new ciphertexts, same total
        </button>
      </figcaption>
    </figure>
  );
}
