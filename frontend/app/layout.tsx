import type { Metadata } from "next";
import { Syne, DM_Sans, DM_Mono } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  display: "swap",
});

const dmMono = DM_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-dm-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Orbit AI — Unified Agentic Workspace",
  description: "Docs, chat, tasks, and AI memory — unified.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`dark ${dmSans.variable} ${syne.variable} ${dmMono.variable}`}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const stored = localStorage.getItem('orbit-theme');
                if (stored) {
                  const parsed = JSON.parse(stored);
                  if (parsed?.state?.theme === 'light') {
                    document.documentElement.classList.remove('dark');
                    document.documentElement.classList.add('light');
                  }
                }
              } catch (e) {}
            `,
          }}
        />
      </head>
      <body className="bg-bg text-orbit-text font-body antialiased selection:bg-accent-dim">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
