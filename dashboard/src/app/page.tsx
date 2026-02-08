import Link from "next/link";
import { getNewsletters, Newsletter } from "@/lib/newsletters";

export default async function Home() {
    const newsletters = await getNewsletters();

    return (
        <main className="container">
            <header className="header">
                <h1>🏕️ 캠핑장 뉴스레터</h1>
                <p>캠핑장 사장님을 위한 주간 뉴스레터 아카이브</p>
            </header>

            {newsletters.length === 0 ? (
                <div className="empty-state">
                    <h2>아직 뉴스레터가 없습니다</h2>
                    <p>첫 번째 뉴스레터가 곧 발행됩니다!</p>
                </div>
            ) : (
                <div className="newsletter-grid">
                    {newsletters.map((newsletter: Newsletter) => (
                        <Link
                            key={newsletter.id}
                            href={`/newsletter/${newsletter.id}`}
                            className="newsletter-card"
                        >
                            <div className="card-header">
                                <span className="card-date">{newsletter.week_info.date}</span>
                                <span className="card-badge">{newsletter.items_count}개 소식</span>
                            </div>
                            <h2 className="card-title">{newsletter.week_info.display}</h2>
                            <p className="card-items-count">
                                {newsletter.items.slice(0, 3).map((item) => item.category).join(" · ")}
                            </p>
                        </Link>
                    ))}
                </div>
            )}
        </main>
    );
}
