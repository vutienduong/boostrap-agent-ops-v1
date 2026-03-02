import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentOps",
  description: "Dev-first AI agent observability",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="border-b bg-white px-8 py-3 flex gap-6 text-sm">
          <a href="/" className="font-medium text-gray-900 hover:text-blue-600">Runs</a>
          <a href="/cost" className="font-medium text-gray-900 hover:text-blue-600">Cost</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
