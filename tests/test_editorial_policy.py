import unittest
from unittest.mock import patch, mock_open
import json
from datetime import datetime
from collectors.base import ContentItem
from ai_filter import _balance_items, _is_hard_rejected, _parse_json_response, prepare_replacement_candidates
from editorial_policy import same_article, evidence_summary, fallback_insight, normalize_insight
from newsletter_generator import get_week_info, generate_newsletter_json, generate_newsletter_text

def review(i):
    return ContentItem(
        title=f"{i} 솔숲 캠핑장 {chr(0xAC00 + i * 50)} 별도 후기",
        url=f"https://blog.naver.com/author{i}/{10000+i}",
        source="네이버 블로그",
        description="화장실 청결과 샤워실 온수가 좋았고 매너타임 순찰이 있었습니다. 아이들이 이용하는 시간에도 공용 공간을 여러 차례 청소하고 소모품을 보충하는 모습을 보았습니다.",
        category="후기인사이트",
        published_date=datetime(2026, 9, 15),
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

    def test_structured_insight_names_the_lesson(self):
        insight = fallback_insight(review(1))
        self.assertTrue(insight["tags"])
        self.assertEqual(insight["customer_signal"], "고객 반응 미확인")
        self.assertIn("적용", insight["lesson"])

    def test_model_insight_is_normalized_for_output(self):
        item = review(1)
        item.insight = normalize_insight({
            "tags": ["시설관리", "고객", "없는 태그"],
            "strength": "개별 시설과 사이트 동선을 함께 안내",
            "customer_signal": "화장실 접근성이 좋았다는 언급",
            "lesson": "시설 차이를 예약 전에 보여주는 점을 배울 수 있습니다.",
            "apply": "사이트별 관리 부담과 안내 방식을 확인합니다.",
        })
        text = generate_newsletter_text([item], get_week_info(datetime(2026, 9, 21)))
        self.assertIn("🏷️ 배울 포인트: 시설 · 고객경험", text)
        self.assertIn("🎯 운영자가 배울 점:", text)
        self.assertIn("🛠️ 적용 전 확인:", text)

    def test_json_parser_normalizes_stringified_records(self):
        response = '[{"index": 0, "summary": "정상"}, "{\\"index\\": 1, \\"summary\\": \\"문자열 객체\\"}", "무시"]'
        parsed = _parse_json_response(response)
        self.assertEqual([item["index"] for item in parsed], [0, 1])

    def test_shortfall_is_visible(self):
        edition = generate_newsletter_json([review(1)], get_week_info(datetime(2026, 9, 21)), [])
        self.assertEqual(edition["quality"]["items_shortfall"], 9)
        self.assertEqual(edition["quality"]["candidates_shortfall"], 30)

    def test_articles_older_than_three_months_or_undated_are_rejected(self):
        from editorial_policy import is_recent_article
        issue_date = datetime(2026, 9, 21)
        self.assertTrue(is_recent_article(review(1), issue_date))
        old = review(2)
        old.published_date = datetime(2026, 6, 20)
        self.assertFalse(is_recent_article(old, issue_date))
        cutoff = review(3)
        cutoff.published_date = datetime(2026, 6, 21)
        self.assertTrue(is_recent_article(cutoff, issue_date))
        undated = review(4)
        undated.published_date = None
        self.assertFalse(is_recent_article(undated, issue_date))
        self.assertTrue(_is_hard_rejected(old))
        self.assertTrue(_is_hard_rejected(undated))

    def test_scheduled_run_preserves_user_deletions(self):
        from main import run_newsletter_pipeline
        for status in ("reviewed", "edited", "replaced", "deleted"):
            existing = json.dumps({"review_status": status, "items": []})
            with patch("main.os.path.exists", return_value=True), patch("builtins.open", mock_open(read_data=existing)), patch("main.collect_all_content") as collect:
                run_newsletter_pipeline(skip_send=True)
                collect.assert_not_called()

    def test_incomplete_old_auto_edition_is_not_preserved(self):
        from main import run_newsletter_pipeline
        existing = json.dumps({
            "review_status": "draft",
            "items": [{"title": "old", "url": "https://example.com/old", "source": "네이버 뉴스", "published_date": "2026-01-01T00:00:00"}],
            "review_candidates": [],
            "quality": {"editorial_version": 3},
        })
        with patch("main.os.path.exists", return_value=True), patch("builtins.open", mock_open(read_data=existing)), patch("main.collect_all_content", return_value=[]):
            run_newsletter_pipeline(skip_send=True)

if __name__ == "__main__":
    unittest.main()
