import type { Metadata } from "next";
import { Newsreader, Inter_Tight, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const serif = Newsreader({ subsets: ["latin"], variable: "--font-newsreader" });
const sans = Inter_Tight({ subsets: ["latin"], variable: "--font-inter-tight" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = { title: "Supply Chain Shockwave" };

const nav = [
  ["Overview", "/"],
  ["Commodities", "/#catalogue"],
  ["Methodology", "/methodology"],
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <header className="border-b border-rule">
          <div className="mx-auto flex max-w-7xl items-baseline justify-between gap-6 px-4 py-3">
            <Link href="/" className="font-serif text-xl tracking-tight">
              Supply Chain <span className="text-signal">Shockwave</span>
            </Link>
            <nav className="flex gap-5 overflow-x-auto text-sm">
              {nav.map(([label, href]) => (
                <Link key={href} href={href} className="whitespace-nowrap text-ink-2 hover:text-ink">
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
        <footer className="border-t border-rule">
          <p className="mx-auto max-w-7xl px-4 py-4 text-xs text-ink-2">
            Prices are monthly benchmark averages, not live quotes. Forecasts are statistical estimates.
          </p>
        </footer>
      </body>
    </html>
  );
}