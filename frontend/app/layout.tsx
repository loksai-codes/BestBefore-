import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  title: 'BestBefore — A best-before date for every AI answer',
  description:
    'A best-before date for every AI answer. AI claims have a shelf life. We stamp each factual claim with a freshness score and an expiry date using Tavily, Bifrost, and FalkorDB.',
  icons: {
    icon: '/icon.svg',
    shortcut: '/icon.svg',
    apple: '/icon.svg',
  },
  openGraph: {
    title: 'BestBefore — A best-before date for every AI answer',
    description:
      'AI claims have a shelf life. Stamp factual claims with freshness scores and shelf-life dates.',
    siteName: 'BestBefore',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased selection:bg-emerald-500/20 selection:text-emerald-300">
        {children}
      </body>
    </html>
  );
}
