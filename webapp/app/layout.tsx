import type { Metadata } from "next";
import { Archivo, Martian_Mono } from "next/font/google";
import "./globals.css";

const archivo = Archivo({ variable: "--font-archivo", subsets: ["latin"], axes: ["wdth"] });
const martian = Martian_Mono({ variable: "--font-martian", subsets: ["latin"], axes: ["wdth"] });

export const metadata: Metadata = {
  title: { default: "AGNIYA: analytics on encrypted data", template: "%s · AGNIYA" },
  description:
    "Exact SUM, AVG, MEDIAN, STDDEV and GROUP BY on customer data that stays encrypted everywhere outside the bank. The server never holds a key; every answer is checked.",
};

const CONTRACT = `<!--
THESIS: Every query prints like a clearing-house message: fields tagged, the total stamped checked, customer rows never on paper. Refuses the dark-navy shield-and-glow security site.
OWN-WORLD: Green-bar fanfold stock (#f3f5ef paper, #dfecda bands), tractor-feed edges, perforated tear lines; ribbon-black figures, red ribbon only for failures, green stamp for checked. Archivo expanded for headers, Martian Mono for figures, tags and ciphertext. Square corners everywhere.
STORY: The visitor sees real ciphertexts made in their own browser, summed blind, decrypted to one checked total; then the pipeline, measured numbers, the SEAL comparison, bank questions, limits; then opens the dashboard.
FIRST VIEWPORT: Left: headline and one-line offer, primary "Open the dashboard". Right: a live printout slip feeding three customer rows into hex, one product, one checked total, with "Print again".
FORM: Green-bar clearing printout, position 7 of 7, seed 988f56c5.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
-->`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${archivo.variable} ${martian.variable} antialiased`}>
        <div hidden dangerouslySetInnerHTML={{ __html: CONTRACT }} />
        {children}
      </body>
    </html>
  );
}
