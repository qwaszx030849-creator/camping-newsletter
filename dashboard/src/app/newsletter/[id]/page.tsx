import Link from "next/link";
import { getNewsletterById, getNewsletters } from "@/lib/newsletters";
import { notFound } from "next/navigation";
import ShareButtons from "@/components/ShareButtons";
import ReviewableNewsletter from "@/components/ReviewableNewsletter";

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
                목록으로 돌아가기
            </Link>

            <article className="newsletter-detail">
                <h1>{newsletter.title}</h1>
                <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
                    발행일 {newsletter.week_info.date} | {newsletter.items_count}개 소식
                </p>

                <ShareButtons
                    newsletter={newsletter}
                    newsletterId={params.id}
                />

                <ReviewableNewsletter
                    newsletter={newsletter}
                    newsletterId={params.id}
                />
            </article>
        </main>
    );
}

export async function generateStaticParams() {
    const newsletters = await getNewsletters();
    return newsletters.map((n) => ({ id: n.id }));
}
