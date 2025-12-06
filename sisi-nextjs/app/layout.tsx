import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SISI - Series Interface",
  description: "A minimal, draggable interface for Series network visualization",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
