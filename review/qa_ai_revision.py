"""Apply source-grounded editorial corrections to this week's AI draft."""
import copy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "review/ai_newsletter_2026_09_week3.json"
data = json.loads(path.read_text(encoding="utf-8"))
old = json.loads((root / "output/newsletter_2026_09_week3.json").read_text(encoding="utf-8"))
previous = {x["url"].rsplit("/", 1)[-1]: x for x in old["items"] + old["review_candidates"]}
for item in data["items"] + data["review_candidates"]:
    item["summary_origin"] = "ai_editorially_reviewed"

replacements = {
    "224415920082": ("224411670207", "온휴캠핑장: 관리자가 자리를 비워도 이용할 수 있는 매점", "후기에서는 체크인을 매점에서 진행하고 시설 이용 방법을 안내받았으며, 관리자가 잠시 자리를 비워도 키오스크로 직접 결제할 수 있었다고 설명합니다. 운영 적용: 매점 무인 운영을 검토한다면 결제 오류와 문의 대응, 재고 확인 담당을 함께 정해두는 사례로 참고할 수 있습니다."),
    "39406": ("224411611245", "한탄강오토캠핑장: 회차별 비품 교체와 기본 설비 확인", "카라반 이용 후기에는 새 수세미와 조리도구가 준비돼 있었고, 냉방과 온수가 잘 작동했다고 나옵니다. 운영 적용: 퇴실 후 청소 체크리스트에 소모품 교체와 냉난방·온수 작동 확인을 별도 항목으로 두고, 다음 입실 전에 완료 여부를 기록하는 방식을 검토할 수 있습니다."),
    "view.php?key=20260720020333923": ("224402875062", "스므나리캠핑장: 개별 편의시설이 있는 구역과 없는 구역 구분", "후기에서는 모든 사이트에 개별 편의시설이 있는 것은 아니며, 해당 시설이 붙은 사이트를 선택할 수 있다고 설명합니다. 운영 적용: 전 구역에 같은 시설을 투자하기 전에 구역별 수요와 관리 부담을 비교하고, 예약 안내에서 시설 포함 여부를 명확히 구분하는 데 참고할 수 있습니다."),
}
for index, item in enumerate(data["review_candidates"]):
    key = item["url"].rsplit("/", 1)[-1]
    if key in replacements:
        old_key, title, summary = replacements[key]
        replacement = copy.deepcopy(previous[old_key])
        replacement.update(title=title, summary=summary, summary_origin="editorial_replacement",
                           selection_reason="플랫폼 관리 또는 시기 불명확 자료를 대신하는 검증된 운영 후기")
        data["review_candidates"][index] = replacement

# Broaden the main edition with shop operations, retaining maintenance as an option.
shop_index = next(i for i, x in enumerate(data["review_candidates"]) if "224411670207" in x["url"])
data["items"][8], data["review_candidates"][shop_index] = data["review_candidates"][shop_index], data["items"][8]

main_edits = [
    ("눌노리체험캠핑장: 체험 사전 접수와 뽑기 이벤트 연계", "방문 후기에는 인절미 체험을 현장 접수 없이 문자로 사전 신청하고, 사이트 번호·이름·나이·희망 일시를 전달했다고 나옵니다. 방문 당시 체험비는 15,000원이었고 참여자에게 뽑기 쿠폰을 추가 지급했습니다. 운영 적용: 접수 항목과 마감 시점을 정하고, 참여 인원에 맞춰 재료·진행 인력을 준비하는 방식으로 참고할 수 있습니다."),
    ("밤개울캠핑장: 한 달 내 재방문 고객의 텐트 보관 사례", "이용자는 한 달 이내 다시 방문하면 텐트를 창고에 보관해도 된다는 안내를 받았고, 다음 방문을 계획했다고 기록했습니다. 운영 적용: 반복 방문 고객의 운반 부담을 줄이는 서비스로 검토하되, 건조 상태·보관 기간·공간 한도·분실 및 훼손 대응을 먼저 정해야 합니다. 전체 고객에게 상시 적용되는 정책인지는 별도 확인이 필요합니다."),
    ("도새울캠핑장: 인접 예약을 살펴 도착 시 대안 사이트 제안", "후기에서는 운영자가 인접한 두 사이트에 일행 팀이 예약한 점을 설명하고, 조용히 머물 수 있는 다른 자리를 여러 곳 제안했다고 나옵니다. 운영 적용: 체크인 전 인접 예약과 빈자리를 확인하고 고객 동의를 받아 대안을 안내하는 절차를 참고할 수 있습니다. 특정 고객의 소음을 단정하거나 일방적으로 자리를 바꾸지 않는 것이 중요합니다."),
    ("하마캠핑장: 가족이 함께 준비하는 할로윈 사탕투어", "과거 방문 후기에는 가족들이 텐트를 꾸미고 사탕을 준비한 뒤 아이들이 사이트를 순회하는 사탕투어와 사과밭 보물찾기가 소개됩니다. 운영 적용: 참여 가족에 포장 방식·준비 수량을 미리 안내하고, 이동 동선·종료 시간·비참여 구역을 정하는 방식을 참고할 수 있습니다. 올해 행사 일정이나 현재 운영 프로그램을 확인한 자료는 아닙니다."),
    ("레인보우캠핑장: 사이트별 그늘과 독립성을 운영자가 안내", "운영자 게시글의 검색 발췌에는 호두·사과 구역의 그늘과 홍시 구역의 타프존 계획, 사이트별 독립성 차이가 설명돼 있습니다. 운영 적용: 예약 안내에 구역별 장점뿐 아니라 그늘이 부족한 시간대와 편의시설까지의 동선도 함께 적는 방식을 참고할 수 있습니다. 발췌의 설치 예정일은 과거 계획으로, 현재 완료 여부는 확인하지 않았습니다."),
    ("또또캠핑장: 사이트에서 보이는 중앙 잔디밭과 소규모 행사", "방문자는 사이트가 중앙 잔디밭을 둘러싸 아이들이 노는 모습을 자리에서 볼 수 있었고, 주말 저녁에 운영자가 신발던지기 행사를 진행했다고 기록했습니다. 운영 적용: 놀이공간을 새로 늘리기 전에 보호자의 시야와 차량 동선이 겹치는 지점을 점검하고, 짧은 공동 프로그램의 준비 시간·진행 인력을 산정해볼 수 있습니다."),
    ("자작자작캠핑장: 개별 울타리에서 운동장으로 이어지는 동선", "A1 이용 후기에서는 사이트 개별 울타리 문을 열면 바로 반려견 운동장으로 이어지는 구조를 장점으로 꼽습니다. 운영 적용: 반려견 동반 구역의 출입문과 운동장 연결 동선을 도면·사진으로 안내하고, 문을 여닫을 때 다른 이용객과 동선이 겹치는 구간을 점검하는 사례로 참고할 수 있습니다."),
    ("캠핑중dog: 매너타임 30분 전 사이트별 사전 안내", "방문 후기에는 운영자가 매너타임인 23시보다 30분 앞서 각 사이트를 돌며 안내하고, 시작 시각을 다시 상기시켰다고 나옵니다. 운영 적용: 예약 메시지에만 규칙을 담기보다 사전 순회 시점과 민원 발생 시 대응 담당을 정해볼 수 있습니다. 순회에 필요한 인력·시간과 고객의 휴식 방해 여부도 함께 검토해야 합니다."),
    None,
    ("가을 캠핑장 관리: 반복되는 낙엽 청소의 우선순위", "운영자 글의 검색 발췌에서는 아침에 낙엽을 치워도 바람이 불면 다시 쌓이는 관리의 어려움을 설명합니다. 운영 적용: 전체 구역을 같은 횟수로 청소하기보다 주요 통행로와 편의시설 출입구를 우선 점검하는 작업 순서를 정해볼 수 있습니다. 실제 청소 주기나 사고 감소 효과가 확인된 자료는 아닙니다."),
]
for item, edit in zip(data["items"], main_edits):
    if edit:
        item.setdefault("original_title", item["title"])
        item["title"], item["summary"] = edit

for item in data["review_candidates"]:
    if "/41271" in item["url"]:
        item["summary"] = "운영자 글의 검색 발췌와 제목에는 13년차 캠지기의 시설동 조명 교체 등 유지관리 업무가 소개됩니다. 운영 적용: 조명·수도·위생시설의 이상 유무와 조치 이력을 정기 점검표에 남기고, 전문 작업이 필요한 경우 담당 업체에 연결하는 기준을 정할 수 있습니다. 전기 작업의 직접 수행을 권하는 자료는 아닙니다."
    if "224411773063" in item["url"]:
        item["summary"] = "후기 제목에는 이른 입실과 저녁 6시 늦퇴실이, 확보한 발췌에는 가을철 밤 줍기가 언급됩니다. 운영 적용: 입퇴실 연장을 제공한다면 앞뒤 예약과 청소 완료 여부에 따른 허용 조건을 미리 정해 안내할 수 있습니다. 모든 날짜에 동일하게 제공되는 혜택인지와 별도 요금 여부는 이 자료만으로 확인되지 않습니다."
        item["evidence_basis"] = "search_excerpt"
    if "224405453028" in item["url"]:
        item["summary"] = "행사 소개글의 발췌에는 빙고·보물찾기·뽑기 등 여러 프로그램을 조합한 할로윈 사례가 나옵니다. 운영 적용: 대상 연령과 진행 시간을 구분한 일정표, 참여비 포함 내역을 미리 안내하는 방식으로 참고할 수 있습니다. 직접 방문 검증이나 올해 행사 확정 공지가 아니므로 개별 캠핑장의 최신 일정과 참가비를 보증하지 않습니다."
    if "224405444523" in item["url"]:
        item["summary"] = "행사 소개글에는 사탕 나눔·텐트 꾸미기·단체사진 등 순서가 있는 프로그램과 별도 참가비 사례가 정리돼 있습니다. 운영 적용: 참가비 여부와 포함 물품, 프로그램 순서를 예약 전에 알려 현장 문의에 대비할 수 있습니다. 지역별 소개글을 운영방식 참고용으로 활용한 것으로, 개별 행사의 현재 진행 여부와 요금은 확인하지 않았습니다."

data["quality"]["ai_summary_count"] = 37
data["quality"]["editorial_replacement_count"] = 3
data["quality"]["editorial_notes"] = "AI 초안 검토 후 플랫폼 관리 2건과 시기 불명확 체험 1건 교체. 사실과 운영 제안을 구분하고 과장된 비용·성과 표현 수정."
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Editorial QA complete: 10 main, 30 candidates; 3 source replacements")
