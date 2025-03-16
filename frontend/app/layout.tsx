import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Tech-Munich25 Speech Processing App',
  description: 'Record, analyze and transcribe speech with phoneme recognition',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="container mx-auto px-4 py-8">
          <header className="mb-8">
            <h1 className="text-3xl font-bold text-center">
              Tech-Munich25 Speech Processing
            </h1>
          </header>
          <main>{children}</main>
          <footer className="mt-8 text-center text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Tech-Munich25
          </footer>
        </div>
      </body>
    </html>
  );
} 