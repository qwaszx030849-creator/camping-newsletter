'use client';

import { useState, useEffect } from 'react';

interface NewsletterItem {
    title: string;
    url: string;
    description: string;
}

interface NewsletterData {
    week_info: {
        display: string;
    };
    items: NewsletterItem[];
}

export default function KakaoPage() {
    const [newsletter, setNewsletter] = useState<NewsletterData | null>(null);
    const [copied, setCopied] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadNewsletter = async () => {
            try {
                // 최신 뉴스레터 JSON 파일들 시도
                const now = new Date();
                const year = now.getFullYear();
                const month = now.getMonth() + 1;

                // 현재 주차와 이전 주차 시도
                for (let week = Math.ceil(now.getDate() / 7); week >= 1; week--) {
                    const filename = `newsletter_${year}_${String(month).padStart(2, '0')}_week${week}.json`;
                    try {
                        const response = await fetch(`/data/${filename}`);
                        if (response.ok) {
                            const data = await response.json();
                            setNewsletter(data);
                            setLoading(false);
                            return;
                        }
                    } catch (e) {
                        continue;
                    }
                }

                setError('최신 뉴스레터를 찾을 수 없습니다.');
            } catch (err) {
                setError('뉴스레터 로드 실패');
            } finally {
                setLoading(false);
            }
        };

        loadNewsletter();
    }, []);

    // 카카오톡 스타일 텍스트 생성
    const generateKakaoText = () => {
        if (!newsletter) return '';

        const lines = [
            '🏕️ 캠핑장 운영 뉴스레터',
            `📅 ${newsletter.week_info?.display || '이번 주'}`,
            '',
            'ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ',
            '',
        ];

        (newsletter.items || []).forEach((item, i) => {
            lines.push(`📌 ${i + 1}. ${item.title}`);
            lines.push('');

            if (item.description) {
                const shortDesc = item.description.length > 50
                    ? item.description.slice(0, 50) + '...'
                    : item.description;
                lines.push(`💬 ${shortDesc}`);
                lines.push('');
            }

            lines.push(`🔗 ${item.url}`);
            lines.push('');
            lines.push('ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ');
            lines.push('');
        });

        lines.push('');
        lines.push('📊 지난 뉴스레터 보기');
        lines.push('👉 camping-newsletter.vercel.app');
        lines.push('');
        lines.push('💡 매주 월요일 발송');

        return lines.join('\n');
    };

    const handleCopy = async () => {
        const text = generateKakaoText();
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-yellow-50 to-amber-100 p-4 md:p-6">
            <div className="max-w-2xl mx-auto">
                {/* 헤더 */}
                <div className="text-center mb-6">
                    <h1 className="text-2xl md:text-3xl font-bold text-amber-800 mb-2">
                        📱 카카오톡 전송용
                    </h1>
                    <p className="text-amber-600 text-sm md:text-base">
                        버튼을 클릭하면 뉴스레터가 복사됩니다
                    </p>
                </div>

                {/* 복사 버튼 */}
                <div className="text-center mb-6">
                    <button
                        onClick={handleCopy}
                        disabled={loading || !!error}
                        className={`
              px-6 md:px-8 py-3 md:py-4 rounded-2xl text-lg md:text-xl font-bold
              transition-all duration-300 transform hover:scale-105
              disabled:opacity-50 disabled:cursor-not-allowed
              ${copied
                                ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                                : 'bg-amber-500 text-white shadow-lg shadow-amber-500/30 hover:bg-amber-600'
                            }
            `}
                    >
                        {loading ? '⏳ 로딩 중...' : copied ? '✅ 복사 완료!' : '📋 뉴스레터 복사하기'}
                    </button>
                </div>

                {/* 에러 메시지 */}
                {error && (
                    <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-3 rounded-xl mb-6 text-center">
                        {error}
                    </div>
                )}

                {/* 미리보기 */}
                <div className="bg-white rounded-2xl shadow-xl p-4 md:p-6 border-2 border-amber-200">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold text-amber-800">📄 미리보기</h2>
                        <span className="text-xs md:text-sm text-gray-500">
                            {newsletter?.week_info?.display || ''}
                        </span>
                    </div>

                    <pre className="
            bg-gray-50 rounded-xl p-3 md:p-4 
            text-xs md:text-sm text-gray-700 
            whitespace-pre-wrap break-words
            font-mono leading-relaxed
            max-h-[400px] md:max-h-[500px] overflow-y-auto
            border border-gray-200
          ">
                        {loading ? '로딩 중...' : generateKakaoText() || '뉴스레터를 불러올 수 없습니다.'}
                    </pre>
                </div>

                {/* 사용 안내 */}
                <div className="mt-6 bg-white/60 rounded-xl p-4 text-center">
                    <p className="text-amber-700 text-xs md:text-sm">
                        💡 <strong>복사 후 카카오톡에 붙여넣기만 하세요!</strong>
                    </p>
                </div>

                {/* 홈으로 돌아가기 */}
                <div className="mt-6 text-center">
                    <a
                        href="/"
                        className="text-amber-600 hover:text-amber-800 underline text-sm"
                    >
                        ← 대시보드로 돌아가기
                    </a>
                </div>
            </div>
        </div>
    );
}
