import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "캠핑장 뉴스레터 아카이브",
    description: "캠핑장 사장님을 위한 주간 뉴스레터 아카이브",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="ko">
            <head>
                <link
                    rel="stylesheet"
                    href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
