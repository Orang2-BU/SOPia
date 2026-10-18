import type { Metadata } from "next";
import "./globals.css";
import "./branding.css";

export const metadata: Metadata = {
  title: "SOPia — SOP yang bisa diajak ngobrol",
  description: "SOP yang bisa diajak ngobrol. Temukan pasal, jalankan proses, dan telusuri setiap keputusan bersama SOPia.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body>{children}</body></html>;
}
