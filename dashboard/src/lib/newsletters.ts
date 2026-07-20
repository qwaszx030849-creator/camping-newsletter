import fs from "fs";
import path from "path";

export interface NewsletterItem {
    title: string;
    url: string;
    source: string;
    description?: string;
    summary?: string;
    published_date?: string;
    category: string;
    score?: number;
}

export interface Newsletter {
    id: string;
    title: string;
    week_info: {
        year: number;
        month: number;
        week: number;
        week_of_month: number;
        date: string;
        display: string;
    };
    created_at: string;
    items: NewsletterItem[];
    items_count: number;
    review_candidates?: NewsletterItem[];
    review_status?: string;
    reviewed_at?: string;
}

// Path to archive directory (inside dashboard)
const ARCHIVE_DIR = path.join(process.cwd(), "data", "archive");

export async function getNewsletters(): Promise<Newsletter[]> {
    const newsletters: Newsletter[] = [];

    try {
        // Check if archive directory exists
        if (!fs.existsSync(ARCHIVE_DIR)) {
            console.log("Archive directory not found:", ARCHIVE_DIR);
            return getSampleNewsletters(); // Return sample data for demo
        }

        // Read all year directories
        const years = fs
            .readdirSync(ARCHIVE_DIR)
            .filter((f) => fs.statSync(path.join(ARCHIVE_DIR, f)).isDirectory());

        for (const year of years) {
            const yearDir = path.join(ARCHIVE_DIR, year);
            const months = fs
                .readdirSync(yearDir)
                .filter((f) => fs.statSync(path.join(yearDir, f)).isDirectory());

            for (const month of months) {
                const monthDir = path.join(yearDir, month);
                const files = fs
                    .readdirSync(monthDir)
                    .filter((f) => f.endsWith(".json"));

                for (const file of files) {
                    try {
                        const content = fs.readFileSync(path.join(monthDir, file), "utf-8");
                        const newsletter = JSON.parse(content) as Newsletter;
                        newsletters.push(newsletter);
                    } catch (e) {
                        console.error(`Error reading ${file}:`, e);
                    }
                }
            }
        }
    } catch (e) {
        console.error("Error reading newsletters:", e);
        return getSampleNewsletters();
    }

    // Sort by date descending
    newsletters.sort(
        (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return newsletters.length > 0 ? newsletters : getSampleNewsletters();
}

export async function getNewsletterById(
    id: string
): Promise<Newsletter | null> {
    const newsletters = await getNewsletters();
    return newsletters.find((n) => n.id === id) || null;
}

// Sample data for demonstration
function getSampleNewsletters(): Newsletter[] {
    return [
        {
            id: "2026-02-week1",
            title: "🏕️ 캠핑장 운영 뉴스레터 - 2026년 2월 1주차",
            week_info: {
                year: 2026,
                month: 2,
                week: 5,
                week_of_month: 1,
                date: "2026-02-03",
                display: "2026년 2월 1주차",
            },
            created_at: "2026-02-03T09:00:00+09:00",
            items: [
                {
                    title: "2026년 친환경 캠핑장 시설개선 지원사업 공고",
                    url: "https://example.com/1",
                    source: "정부24",
                    description:
                        "중소기업청에서 친환경 캠핑장 시설개선을 위한 보조금 지원사업을 공고했습니다. 최대 5천만원까지 지원되며, 신청기간은 2월 15일부터 3월 15일까지입니다.",
                    category: "정책",
                },
                {
                    title: "글램핑 시장 전년 대비 30% 성장",
                    url: "https://example.com/2",
                    source: "한국경제",
                    description:
                        "한국관광공사 발표에 따르면 글램핑 시장이 작년 대비 30% 성장했습니다. 특히 반려동물 동반 글램핑 수요가 급증했습니다.",
                    category: "트렌드",
                },
                {
                    title: "캠핑장 화재 예방 가이드라인 개정",
                    url: "https://example.com/3",
                    source: "소방청",
                    description:
                        "소방청에서 캠핑장 화재 예방을 위한 새로운 가이드라인을 발표했습니다. 난방기구 사용 규정이 강화되었습니다.",
                    category: "정책",
                },
            ],
            items_count: 3,
        },
    ];
}
