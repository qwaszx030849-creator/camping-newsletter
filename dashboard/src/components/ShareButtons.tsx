"use client";

import { useState } from "react";

interface ShareButtonsProps {
    newsletter: {
        title: string;
        week_info: {
            display: string;
            date: string;
        };
        items: Array<{
            title: string;
            url: string;
            source: string;
            description?: string;
            category: string;
        }>;
    };
    newsletterId: string;
}

export default function ShareButtons({ newsletter, newsletterId }: ShareButtonsProps) {
    const [copied, setCopied] = useState(false);
    const [showToast, setShowToast] = useState(false);

    // 뉴스레터 텍스트 생성
    const generateNewsletterText = () => {
        let text = `🏕️ 캠핑장 운영 뉴스레터\n`;
        text += `${newsletter.week_info.display}\n\n`;
        text += `━━━━━━━━━━━━━━━━━━━━\n\n`;

        newsletter.items.forEach((item, index) => {
            text += `${index + 1}. [${item.category}] ${item.title}\n`;
            if (item.description) {
                text += `   📌 ${item.description.slice(0, 100)}...\n`;
            }
            text += `   🔗 ${item.url}\n\n`;
        });

        text += `━━━━━━━━━━━━━━━━━━━━\n`;
        text += `📊 전체 뉴스레터 보기: ${typeof window !== 'undefined' ? window.location.origin : ''}/newsletter/${newsletterId}`;

        return text;
    };

    // 클립보드에 복사
    const handleCopy = async () => {
        const text = generateNewsletterText();
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setShowToast(true);
            setTimeout(() => {
                setCopied(false);
                setShowToast(false);
            }, 2000);
        } catch (err) {
            console.error("Failed to copy:", err);
        }
    };

    // 카카오톡 공유 (웹 공유 API 사용)
    const handleKakaoShare = () => {
        const text = generateNewsletterText();
        const url = typeof window !== 'undefined' ? window.location.href : '';

        // 카카오톡 공유 링크 (모바일)
        if (navigator.share) {
            navigator.share({
                title: newsletter.title,
                text: text.slice(0, 200) + '...',
                url: url,
            }).catch(console.error);
        } else {
            // PC에서는 카카오톡 공유하기 URL 사용
            const kakaoUrl = `https://story.kakao.com/share?url=${encodeURIComponent(url)}`;
            window.open(kakaoUrl, '_blank', 'width=500,height=600');
        }
    };

    // URL 복사
    const handleCopyUrl = async () => {
        const url = typeof window !== 'undefined' ? window.location.href : '';
        try {
            await navigator.clipboard.writeText(url);
            setShowToast(true);
            setTimeout(() => setShowToast(false), 2000);
        } catch (err) {
            console.error("Failed to copy URL:", err);
        }
    };

    return (
        <div className="share-container">
            <div className="share-buttons">
                <button
                    onClick={handleCopy}
                    className="share-btn copy-btn"
                    title="뉴스레터 전체 텍스트 복사"
                >
                    {copied ? "✅ 복사됨!" : "📋 뉴스레터 복사"}
                </button>

                <button
                    onClick={handleCopyUrl}
                    className="share-btn url-btn"
                    title="링크 복사"
                >
                    🔗 링크 복사
                </button>

                <button
                    onClick={handleKakaoShare}
                    className="share-btn kakao-btn"
                    title="카카오톡/SNS 공유"
                >
                    💬 공유하기
                </button>
            </div>

            {showToast && (
                <div className="toast">
                    ✅ 클립보드에 복사되었습니다!
                </div>
            )}

            <style jsx>{`
                .share-container {
                    position: relative;
                    margin-bottom: 2rem;
                }
                
                .share-buttons {
                    display: flex;
                    gap: 0.75rem;
                    flex-wrap: wrap;
                }
                
                .share-btn {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.75rem 1.25rem;
                    border: none;
                    border-radius: 8px;
                    font-size: 0.9rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .copy-btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                
                .copy-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                }
                
                .url-btn {
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                }
                
                .url-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4);
                }
                
                .kakao-btn {
                    background: linear-gradient(135deg, #fee140 0%, #fa709a 100%);
                    color: #333;
                }
                
                .kakao-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(254, 225, 64, 0.4);
                }
                
                .toast {
                    position: fixed;
                    bottom: 2rem;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #333;
                    color: white;
                    padding: 1rem 2rem;
                    border-radius: 8px;
                    font-weight: 500;
                    z-index: 1000;
                    animation: fadeIn 0.3s ease;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(10px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(0); }
                }
                
                @media (max-width: 640px) {
                    .share-buttons {
                        flex-direction: column;
                    }
                    
                    .share-btn {
                        width: 100%;
                        justify-content: center;
                    }
                }
            `}</style>
        </div>
    );
}
