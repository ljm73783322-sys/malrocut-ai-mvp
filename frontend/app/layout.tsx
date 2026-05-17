import "./globals.css";
import { ReactNode } from "react";

export const metadata = {
  title: "말로컷 AI",
  description: "말로 하는 쉬운 영상 편집",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen flex flex-col items-center p-4">
        <header className="w-full max-w-4xl py-6 mb-8 text-center bg-white rounded-xl shadow-sm">
          <h1 className="text-4xl font-bold text-blue-600">말로컷 AI</h1>
          <p className="text-xl text-gray-500 mt-2">복잡한 편집 없이 말로 다 하는 마법</p>
        </header>
        <main className="w-full max-w-4xl bg-white p-8 rounded-xl shadow-md flex-1">
          {children}
        </main>
      </body>
    </html>
  );
}
