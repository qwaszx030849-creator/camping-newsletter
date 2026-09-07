"use client";

import { useMemo, useState } from "react";
import { Newsletter, NewsletterItem } from "@/lib/newsletters";

interface Props {
    newsletter: Newsletter;
    newsletterId: string;
}

type ReviewItem = NewsletterItem & { originalSlot: number };

interface ReplacementLog {
    type: "replace";
    slot: number;
    removed: NewsletterItem;
    replacement: NewsletterItem;
}

interface DeletionLog {
    type: "delete";
    slot: number;
    removed: NewsletterItem;
}

type ChangeLog = ReplacementLog | DeletionLog;

const stripReviewMeta = ({ originalSlot: _originalSlot, ...item }: ReviewItem): NewsletterItem => item;

export default function ReviewableNewsletter({ newsletter, newsletterId }: Props) {
    const [items, setItems] = useState<ReviewItem[]>(
        newsletter.items.map((item, index) => ({ ...item, originalSlot: index + 1 }))
    );
    const [candidateCursor, setCandidateCursor] = useState(0);
    const [excluded, setExcluded] = useState<number[]>([]);
    const [deleted, setDeleted] = useState<number[]>([]);
    const [changes, setChanges] = useState<ChangeLog[]>([]);
    const [copied, setCopied] = useState("");

    const candidates = newsletter.review_candidates || [];
    const usedUrls = useMemo(() => new Set(items.map((item) => item.url)), [items]);

    const fileName = `newsletter_${newsletter.week_info.year}_${String(newsletter.week_info.month).padStart(2, "0")}_week${newsletter.week_info.week_of_month}.json`;
    const commandParts = [`python review_replacements.py --file output/${fileName}`];
    if (excluded.length) commandParts.push(`--exclude ${excluded.join(" ")}`);
    if (deleted.length) commandParts.push(`--delete ${deleted.join(" ")}`);
    const reviewCommand = commandParts.join(" ");

    const findNextCandidate = (cursor: number) => {
        for (let i = cursor; i < candidates.length; i += 1) {
            if (candidates[i]?.url && !usedUrls.has(candidates[i].url)) {
                return { candidate: candidates[i], nextCursor: i + 1 };
            }
        }
        return { candidate: null, nextCursor: cursor };
    };

    const deleteItem = (index: number) => {
        const removed = items[index];
        if (!removed) return;
        setItems((prev) => prev.filter((_, itemIndex) => itemIndex !== index));
        setDeleted((prev) => [...prev, removed.originalSlot]);
        setChanges((prev) => [...prev, { type: "delete", slot: removed.originalSlot, removed: stripReviewMeta(removed) }]);
    };

    const replaceItem = (index: number) => {
        const { candidate, nextCursor } = findNextCandidate(candidateCursor);
        if (!candidate) {
            deleteItem(index);
            setCopied("대체 후보가 없어 삭제로 제외했습니다.");
            setTimeout(() => setCopied(""), 1800);
            return;
        }

        const removed = items[index];
        const nextItems = [...items];
        nextItems[index] = { ...candidate, originalSlot: removed.originalSlot };
        setItems(nextItems);
        setCandidateCursor(nextCursor);
        setExcluded((prev) => [...prev, removed.originalSlot]);
        setChanges((prev) => [
            ...prev,
            { type: "replace", slot: removed.originalSlot, removed: stripReviewMeta(removed), replacement: candidate },
        ]);
    };

    const copyCommand = async () => {
        if (excluded.length === 0 && deleted.length === 0) {
            setCopied("먼저 교체 또는 삭제할 기사를 선택하세요.");
            setTimeout(() => setCopied(""), 1800);
            return;
        }
        await navigator.clipboard.writeText(reviewCommand);
        setCopied("검토 명령을 복사했습니다.");
        setTimeout(() => setCopied(""), 1800);
    };

    const copyReviewedJson = async () => {
        const reviewed = {
            ...newsletter,
            items: items.map(stripReviewMeta),
            items_count: items.length,
            review_status: changes.length ? "preview_edited" : newsletter.review_status || "draft",
            review_changes_preview: changes.map((change) =>
                change.type === "delete"
                    ? {
                          type: change.type,
                          slot: change.slot,
                          removed: { title: change.removed.title, url: change.removed.url },
                      }
                    : {
                          type: change.type,
                          slot: change.slot,
                          removed: { title: change.removed.title, url: change.removed.url },
                          replacement: { title: change.replacement.title, url: change.replacement.url },
                      }
            ),
        };
        await navigator.clipboard.writeText(JSON.stringify(reviewed, null, 2));
        setCopied("검토본 JSON을 복사했습니다.");
        setTimeout(() => setCopied(""), 1800);
    };

    return (
        <section className="review-section">
            <div className="review-toolbar">
                <div>
                    <strong>검토 모드</strong>
                    <span>현재 {items.length}개 · 대체 후보 {candidates.length}개 · 삭제는 후보 없이 바로 제외</span>
                </div>
                <div className="review-actions">
                    <button type="button" onClick={copyCommand} disabled={excluded.length === 0 && deleted.length === 0}>
                        검토 명령 복사
                    </button>
                    <button type="button" onClick={copyReviewedJson}>
                        검토본 JSON 복사
                    </button>
                </div>
            </div>

            {changes.length > 0 ? (
                <div className="change-log">
                    {changes.map((change, index) => (
                        <p key={`${change.type}-${change.slot}-${index}`}>
                            {change.type === "delete"
                                ? `${change.slot}번 삭제: ${change.removed.title}`
                                : `${change.slot}번 교체: ${change.removed.title} → ${change.replacement.title}`}
                        </p>
                    ))}
                </div>
            ) : null}

            {excluded.length > 0 || deleted.length > 0 ? (
                <pre className="review-command">{reviewCommand}</pre>
            ) : null}

            <div className="item-list">
                {items.map((item, index) => (
                    <div key={`${item.url}-${index}`} className="item-card">
                        <div className="item-card-header">
                            <span className={`item-category ${item.category}`}>
                                {item.category || "기타"}
                            </span>
                            <div className="item-review-actions">
                                <button
                                    type="button"
                                    className="replace-button"
                                    onClick={() => replaceItem(index)}
                                    title="이 기사를 제외하고 후보 기사로 대체"
                                >
                                    교체
                                </button>
                                <button
                                    type="button"
                                    className="delete-button"
                                    onClick={() => deleteItem(index)}
                                    title="이 기사를 대체 없이 삭제"
                                >
                                    삭제
                                </button>
                            </div>
                        </div>
                        <h3 className="item-title">{item.title}</h3>
                        {item.summary ? (
                            <p className="item-description" style={{ fontWeight: 500, lineHeight: 1.7 }}>
                                {item.summary}
                            </p>
                        ) : item.description ? (
                            <p className="item-description">{item.description}</p>
                        ) : null}
                        <p className="item-source">출처: {item.source}</p>
                        <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="item-link"
                        >
                            원문 보기
                        </a>
                    </div>
                ))}
            </div>

            {copied ? <div className="toast">{copied}</div> : null}

            <style jsx>{`
                .review-section {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }

                .review-toolbar {
                    display: flex;
                    justify-content: space-between;
                    gap: 1rem;
                    align-items: center;
                    padding: 1rem;
                    border: 1px solid var(--card-border);
                    background: rgba(255, 255, 255, 0.04);
                    border-radius: 8px;
                }

                .review-toolbar strong {
                    display: block;
                    margin-bottom: 0.25rem;
                }

                .review-toolbar span {
                    color: var(--text-muted);
                    font-size: 0.85rem;
                }

                .review-actions,
                .item-review-actions {
                    display: flex;
                    gap: 0.5rem;
                    flex-wrap: wrap;
                }

                .review-actions button,
                .replace-button,
                .delete-button {
                    border: 1px solid var(--card-border);
                    border-radius: 6px;
                    background: #111827;
                    color: var(--foreground);
                    cursor: pointer;
                    font-weight: 700;
                }

                .review-actions button {
                    padding: 0.65rem 0.85rem;
                }

                .replace-button,
                .delete-button {
                    height: 2rem;
                    min-width: 3rem;
                    padding: 0 0.55rem;
                    font-size: 0.75rem;
                }

                .replace-button {
                    color: #bfdbfe;
                    border-color: rgba(96, 165, 250, 0.55);
                }

                .delete-button {
                    color: #fecaca;
                    border-color: rgba(248, 113, 113, 0.45);
                }

                .review-actions button:disabled {
                    opacity: 0.45;
                    cursor: not-allowed;
                }

                .item-card-header {
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 0.75rem;
                }

                .replace-button:hover {
                    background: #1d4ed8;
                    color: white;
                }

                .delete-button:hover {
                    background: #7f1d1d;
                    color: white;
                }

                .change-log,
                .review-command {
                    border: 1px solid var(--card-border);
                    background: rgba(0, 0, 0, 0.25);
                    border-radius: 8px;
                    padding: 1rem;
                    color: var(--text-muted);
                    font-size: 0.85rem;
                    white-space: pre-wrap;
                }

                .change-log p + p {
                    margin-top: 0.5rem;
                }

                .toast {
                    position: fixed;
                    bottom: 2rem;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #111827;
                    color: white;
                    padding: 0.9rem 1.25rem;
                    border-radius: 8px;
                    border: 1px solid var(--card-border);
                    z-index: 1000;
                }

                @media (max-width: 720px) {
                    .review-toolbar {
                        align-items: stretch;
                        flex-direction: column;
                    }

                    .review-actions button {
                        flex: 1;
                    }
                }
            `}</style>
        </section>
    );
}
