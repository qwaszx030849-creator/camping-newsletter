import Link from "next/link";
import { getNewsletterById, Newsletter } from "@/lib/newsletters";
import { notFound } from "next/navigation";
import ShareButtons from "@/components/ShareButtons";

interface PageProps {
    params: { id: string };
}

export default async function NewsletterDetail({ params }: PageProps) {
    const newsletter = await getNewsletterById(params.id);

    if (!newsletter) {
        notFound();
    }

    return (
        <main className="container">
            <Link href="/" className="back-link">
                ← 목록으로 돌아가기
            </Link>

            <article className="newsletter-detail">
                <h1>{newsletter.title}</h1>
                <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
                    발행일: {newsletter.week_info.date} | {newsletter.items_count}개 소식
                </p>

                {/* 복사/공유 버튼 */}
                <ShareButtons
                    newsletter={newsletter}
                    newsletterId={params.id}
                />

                <div className="item-list">
                    {newsletter.items.map((item, index) => (
                        <div key={index} className="item-card">
                            <span className={`item-category ${item.category}`}>
                                {item.category || "기타"}
                            </span>
                            <h3 className="item-title">{item.title}</h3>
                            {item.description && (
                                <p className="item-description">{item.description}</p>
                            )}
                            <p className="item-source">출처: {item.source}</p>
                            <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="item-link"
                            >
                                원본 보기 →
                            </a>
                        </div>
                    ))}
                </div>
            </article>
        </main>
    );
}

export async function generateStaticParams() {
    // For static generation, return empty array (will use fallback)
    return [];
}

