import unittest
from unittest.mock import patch
from datetime import datetime
from collectors.base import ContentItem
from ai_filter import _balance_items, _is_hard_rejected, prepare_replacement_candidates
from editorial_policy import same_article, evidence_summary
from newsletter_generator import get_week_info, generate_newsletter_json

def review(i):
    return ContentItem(
        title=f"{i} 솔숲 캠핑장 {chr(0xAC00 + i * 50)} 별도 후기",
        url=f"https://blog.naver.com/author{i}/{10000+i}",
        source="네이버 블로그",
        description="화장실 청결과 샤워실 온수가 좋았고 매너타임 순찰이 있었습니다.",
        category="후기인사이트",
    )

class EditorialTests(unittest.TestCase):
    def test_ten_reviews_are_not_capped_at_four(self):
        pool = [review(i) for i in range(12)]
        self.assertEqual(len(_balance_items(pool, pool, 10)), 10)

    def test_shared_amenities_are_not_duplicates(self):
        self.assertFalse(same_article(review(1), review(9)))

    def test_duplicate_url_alias(self):
        first = review(1)
        second = review(2)
        second.url = first.url.replace("blog.naver", "m.blog.naver")
        self.assertTrue(same_article(first, second))

    def test_competitor_and_platform_promo_always_excluded(self):
        for title in ("그래가 협찬 캠핑장 후기", "NOL 캠핑장 단독 예약 후기", "캠핑장 파크골프 후기"):
            item = review(1)
            item.title = title
            self.assertTrue(_is_hard_rejected(item))

    def test_halloween_is_allowed(self):
        item = review(1)
        item.title = "숲속 캠핑장 할로윈 체험 후기"
        self.assertFalse(_is_hard_rejected(item))

    def test_replacement_pool_can_contain_thirty_reviews(self):
        pool = [review(i) for i in range(40)]
        candidates = prepare_replacement_candidates(pool, pool[:10])
        self.assertEqual(len(candidates), 30)
        self.assertFalse({x.url for x in candidates} & {x.url for x in pool[:10]})

    def test_fallback_separates_evidence_and_suggestions(self):
        summary = evidence_summary(review(1))
        self.assertIn("확인된 자료 발췌:", summary)
        self.assertIn("운영 적용 제안:", summary)
        self.assertNotIn("매출 상승", summary)

    def test_shortfall_is_visible(self):
        edition = generate_newsletter_json([review(1)], get_week_info(datetime(2026, 9, 21)), [])
        self.assertEqual(edition["quality"]["items_shortfall"], 9)
        self.assertEqual(edition["quality"]["candidates_shortfall"], 30)

if __name__ == "__main__":
    unittest.main()
