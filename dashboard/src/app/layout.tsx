import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/sidebar";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "STIX Fabric Console",
  description: "Premium policy fabric console for AI agent authorization",
  icons: {
    icon: "/favicon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={spaceGrotesk.className}>
        <Providers>
          <div className="min-h-screen overflow-x-hidden bg-[var(--stix-bg)] text-slate-950">
            <Sidebar />
            <main className="min-h-screen pb-24 lg:pb-0 lg:pl-72">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
