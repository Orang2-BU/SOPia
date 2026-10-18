import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SOPia — Asisten Proses SOP",
  description: "Asisten proses kerja berbasis SOP dengan persetujuan dan jejak audit.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body>{children}</body></html>;
}
