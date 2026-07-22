import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "平安线计划题库",
  description: "用于维护、审核、导入导出和随机组卷的内部题库工具。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
