import unittest
from unittest.mock import patch, mock_open
import json
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
        description="화장실 청결과 샤워실 온수가 좋았고 매너타임 순찰이 있었습니다. 아이들이 이용하는 시간에도 공용 공간을 여러 차례 청소하고 소모품을 보충하는 모습을 보았습니다.",
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

    def test_review_words_do_not_exempt_ads_or_wild_camping(self):
        for title in ("무료 노지 캠핑장 후기", "캠핑장 제휴 마케팅 후기", "클라이언트 캠핑장 매출 후기"):
            item = review(1)
            item.title = title
            self.assertTrue(_is_hard_rejected(item))

    def test_sponsorship_hidden_in_body_is_excluded(self):
        from collectors.public_review import enrich_public_reviews
        with patch("collectors.public_review.requests.get") as get:
            get.return_value.text = '<div class="se-main-container"><p>숙박을 제공받아 작성한 후기입니다.</p></div>'
            self.assertEqual(enrich_public_reviews([review(1)]), [])

    def test_public_body_evidence_is_recorded(self):
        from collectors.public_review import enrich_public_reviews
        with patch("collectors.public_review.requests.get") as get:
            get.return_value.text = '<div class="se-main-container"><p>매너타임에는 관리자가 직접 순찰하며 소음이 나는 사이트에 안내했습니다.</p></div>'
            result = enrich_public_reviews([review(1)])
            self.assertEqual(result[0].evidence_basis, "public_blog_body")
            self.assertIn("직접 순찰", result[0].description)

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

    def test_scheduled_run_preserves_user_deletions(self):
        from main import run_newsletter_pipeline
        for status in ("reviewed", "edited", "replaced", "deleted"):
            existing = json.dumps({"review_status": status, "items": []})
            with patch("main.os.path.exists", return_value=True), patch("builtins.open", mock_open(read_data=existing)), patch("main.collect_all_content") as collect:
                run_newsletter_pipeline(skip_send=True)
                collect.assert_not_called()

if __name__ == "__main__":
    unittest.main()
