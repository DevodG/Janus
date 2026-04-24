import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "JANUS — Living Intelligence System",
  description: "Multi-agent AI cognitive interface — research, simulate, and analyze with autonomous intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="h-full font-sans" style={{ background: 'var(--janus-bg)', color: 'var(--janus-text)' }}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
