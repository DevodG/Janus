import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import JanusSidebar from "@/components/layout/JanusSidebar";
import Particles from "@/components/layout/Particles";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "JANUS — AGI Cognitive Interface",
  description: "MiroOrg Intelligence System — research, simulate, and analyze with multi-agent AI orchestration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full bg-gray-950 text-gray-100 font-sans">
        <Particles />
        <JanusSidebar />
        <main className="pt-12 min-h-screen relative z-10">
          {children}
        </main>
      </body>
    </html>
  );
}
