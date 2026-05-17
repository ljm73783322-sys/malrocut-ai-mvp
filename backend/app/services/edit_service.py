from .job_store import jobs_db

def create_edit_plan_mock(job_id: str, prompt: str):
    plan = {
        "subtitle_action": "기존 자막 가림 및 노란색 큰 글씨 새 자막 삽입",
        "cut_action": "무음 구간 3곳 컷 편집 완료",
        "style_action": "얼굴 중앙 확대 및 화사한 색감 적용"
    }
    jobs_db[job_id]["plan"] = plan
    return plan
