import os
import json
import streamlit as st
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# =========================================================
# 환경 변수 로드
# =========================================================
load_dotenv()

# =========================================================
# 분류 프롬프트 (원본과 동일)
# =========================================================
def create_classification_prompt() -> str:
    return """
1. 역할 정의
당신은 광고 텍스트를 분석해 사전 정의된 파라미터 스키마에 따라 JSON으로 분류하는 분류기입니다.
출력은 반드시 유효한 JSON 한 덩어리로만 반환해야 하며, 설명 문장은 notes 필드에만 기록합니다.

2. 출력 스키마
{
  "ad_type": "",
  "ad_type_category": [],
  "ad_theme": [],
  "target_age": "",
  "target_gender": "",
  "motivation": {
    "fun": 0, "social": 0, "rewards": 0, "savings": 0, "trust": 0,
    "convenience": 0, "growth": 0, "status_display": 0, "curiosity": 0,
    "habit_building": 0, "safety_net": 0
  },
  "engagement": {
    "casual_score": 0.0, "hardcore_score": 0.0, "frequency_score": 0.0,
    "multi_app_usage": 0, "retention_potential": 0.0,
    "session_length_expectation": "short"
  },
  "promo": {
    "install_reward_sensitive": 0, "coupon_event_sensitive": 0,
    "fomo_sensitive": 0, "exclusive_benefit_sensitive": 0,
    "trial_experience_sensitive": 0
  },
  "brand": {
    "brand_loyalty": 0.0, "nostalgia": 0, "trust_in_official": 0.0,
    "award_proof_sensitive": 0, "local_trust_factor": 0.0,
    "global_trust_factor": 0.0
  },
  "commerce": {
    "price_sensitivity": 0.0, "premium_willingness": 0.0,
    "transaction_frequency": 0.0, "risk_tolerance": 0.0,
    "recurring_payment": 0, "big_purchase_intent": 0.0
  },
  "notes": []
}

3. 분류 규칙
(A) 광고 유형 ad_type
1:설치형 → 1
2:실행형 → 2
3:참여형 → 3
4:클릭형 → 4
5:페북 → 5
6:트위터 → 6
7:인스타 → 7
8:노출형 → 8
9:퀘스트 → 9
10:유튜브 → 10
11:네이버 → 11
12:CPS(물건구매) → 12

(B) 광고 카테고리 ad_type_category
0: 카테고리 선택안함 → 0
1: 앱(간편적립) → 1
2: 경험하기(게임적립)/앱(간편적립) - cpi,cpe → 2
3: 구독(간편적립) → 3
4: 간편미션-퀴즈(간편적립) → 4
5: 경험하기(게임적립) - cpa → 5
6: 멀티보상(게임적립) → 6
7: 금융(참여적립) → 7
8: 무료참여(참여적립) → 8
10: 유료참여(참여적립) → 10
11: 쇼핑-상품별카테고리(쇼핑적립) → 11
12: 제휴몰(쇼핑적립) → 12
13: 간편미션(간편적립) → 13
`
(C) 광고 테마 ad_theme
서사·정서·소구 포인트 태깅, 복수 가능
예: 판타지 RPG → fantasy, competition, growth
예: 보험 → trust, safety_net, security_privacy
예: 리워드 → rewards, savings_benefit, urgency

(D) 연령 target_age
명시 있으면 그대로 반영 (예: 13~18세 → teens)
단서 없으면 → all_ages
보험, 금융 → 기본 thirties 이상 추정 가능

(E) 성별 target_gender
명시 없으면 기본 neutral
여성용 뷰티/패션 강조 → female_focus
남성 전용 서비스(면도, 밀리터리) → male_focus

4. 파라미터 값 판정 기준
핵심 원칙: 명시적 키워드가 없더라도, 광고 유형(ad_type)과 문맥을 바탕으로 관련성이 높은 항목에 대해서는 0 대신 합리적인 기본 점수(예: 0.2~0.5)를 적극적으로 부여한다.

Motivation
- rewards: '적립', '보상' 언급 시 1. 'shopping', 'game' 유형 광고는 문맥상 암시만 있어도 0.3 이상 추론.
- savings: '할인', '최저가' 언급 시 1. 'shopping' 유형 광고는 가격 소구 가능성이 높으므로 기본 0.3 이상 추론.
- fun: 'game' 광고는 명시적 단어 없어도 기본 0.7 이상 부여. 엔터테인먼트, 'content' 유형도 0.3 이상 추론.
- trust: 'finance', 'healthcare' 광고는 신뢰가 중요하므로 기본 0.5 이상 부여. '공식', '인증' 등 언급 시 1.
- growth: 'education', 'game'(특히 RPG) 유형은 성장 요소가 내재되어 있으므로 기본 0.4 이상 추론.
- curiosity: '무료 체험', '새로운 기능' 등 언급 시 1. 신규 앱/서비스 광고는 호기심 유발 가능성이 높으므로 0.2 이상 추론.

Commerce
- price_sensitivity: 'shopping' 광고는 대부분 가격에 민감한 사용자를 타겟하므로 기본 0.6 이상 부여. '최저가', '할인' 강조 시 0.9 이상.
- risk_tolerance: 'finance' 중 투자, 가상화폐 관련 광고는 리스크 감수 성향이 중요하므로 0.8 이상 부여. '보험'은 리스크 회피이므로 이 항목은 0.1 이하로 유지.
- big_purchase_intent: 'finance'(대출, 보험), 'real_estate' 등 고가 상품/서비스는 0.7 이상 부여.

Brand
- brand_loyalty, trust_in_official: '아모레퍼시픽', '삼성' 등 대중에게 알려진 기업/브랜드 이름이 언급되면, '유명 브랜드'라는 직접적 표현이 없어도 0.5 이상 부여. 'finance' 유형은 기본 0.3 이상 추론.
- local_trust_factor: 광고 주체가 국내 기업으로 명확히 인지되면 1 부여.

5. 출력 규칙
항상 JSON만 출력 (추가 설명 금지).
notes 필드에 분류 근거 키워드를 짧게 기록.
가장 중요한 것은 문맥을 파악하여 0으로 비워두기보다, 관련성이 조금이라도 있다면 적극적으로 값을 추론해 채우는 것이다.

6. 사용자 지정 정보 활용
- "사용자 지정 광고 유형"이 제공된 경우, 해당 값을 ad_type으로 사용하되 문맥상 부적절하면 재분류
- "사용자 지정 광고 카테고리"가 제공된 경우, 해당 값을 ad_type_category에 포함
- 사용자 지정 정보가 없으면 광고 텍스트를 바탕으로 자동 분류

다음 광고 텍스트를 분석하여 위 스키마에 맞는 JSON을 반환하세요:
""".strip()

# =========================================================
# Gemini API 호출 함수 (원본과 동일)
# =========================================================
def call_gemini_json(prompt_text: str,
                     api_key: str,
                     model: str = "gemini-1.5-flash-8b",
                     timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Gemini에 프롬프트를 전달하고, JSON 응답을 안전하게 추출합니다.
    JSON 코드펜스가 있을 경우 제거합니다.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt_text}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2000
        }
    }

    resp = requests.post(f"{url}?key={api_key}", headers=headers, json=body, timeout=timeout)
    if resp.status_code != 200:
        st.error(f"Gemini API 오류: status={resp.status_code}")
        return None

    data = resp.json()
    cands = data.get("candidates", [])
    if not cands:
        st.error("Gemini 응답에 candidates가 없습니다.")
        return None

    parts = cands[0].get("content", {}).get("parts", [])
    if not parts:
        st.error("Gemini 응답에 parts가 없습니다.")
        return None

    text = parts[0].get("text", "")
    if not text:
        st.error("Gemini 응답에 text가 없습니다.")
        return None

    raw = text.strip()
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    # 최종 JSON 파싱
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 간단 복구: 앞/뒤 설명 제거 가능성이 있으므로 중괄호 범위만 추출 시도
        try:
            first = cleaned.find("{")
            last = cleaned.rfind("}")
            if first != -1 and last != -1 and last > first:
                sliced = cleaned[first:last+1]
                return json.loads(sliced)
        except Exception:
            pass
        st.error(f"JSON 파싱 실패. 원문 일부: {cleaned[:500]}")
        return None

# =========================================================
# 한국어 변환 함수들
# =========================================================
def get_korean_ad_type(ad_type):
    """광고 유형을 한국어로 변환"""
    ad_type_map = {
        "1": "설치형", "2": "실행형", "3": "참여형", "4": "클릭형", 
        "5": "페북", "6": "트위터", "7": "인스타", "8": "노출형", 
        "9": "퀘스트", "10": "유튜브", "11": "네이버", "12": "CPS(물건구매)",
        "game": "게임", "app": "앱", "shopping": "쇼핑", "finance": "금융",
        "service": "서비스", "content": "콘텐츠", "healthcare": "헬스케어",
        "education": "교육", "rewards_only": "리워드 전용", "other": "기타"
    }
    return ad_type_map.get(ad_type, ad_type)

def get_korean_target_age(target_age):
    """타겟 연령을 한국어로 변환"""
    age_map = {
        "all_ages": "전연령", "teens": "10대", "twenties": "20대", "thirties": "30대", 
        "forties": "40대", "fifties": "50대", "adults": "성인"
    }
    return age_map.get(target_age, target_age)

def get_korean_target_gender(target_gender):
    """타겟 성별을 한국어로 변환"""
    gender_map = {
        "male_focus": "남성 중심", "female_focus": "여성 중심", 
        "male": "남성", "female": "여성", "neutral": "전성별"
    }
    return gender_map.get(target_gender, target_gender)

def get_korean_categories(categories):
    """카테고리를 한국어로 변환"""
    category_map = {
        "0": "카테고리 선택안함", "1": "앱(간편적립)", 
        "2": "경험하기(게임적립)/앱(간편적립)", "3": "구독(간편적립)",
        "4": "간편미션-퀴즈(간편적립)", "5": "경험하기(게임적립)",
        "6": "멀티보상(게임적립)", "7": "금융(참여적립)",
        "8": "무료참여(참여적립)", "10": "유료참여(참여적립)",
        "11": "쇼핑-상품별카테고리(쇼핑적립)", "12": "제휴몰(쇼핑적립)",
        "13": "간편미션(간편적립)"
    }
    
    if isinstance(categories, list):
        korean_categories = [category_map.get(str(cat), str(cat)) for cat in categories]
        return ", ".join(korean_categories) if korean_categories else "N/A"
    else:
        return category_map.get(str(categories), str(categories)) if categories else "N/A"

def get_korean_themes(themes):
    """테마를 한국어로 변환"""
    theme_map = {
        "fantasy": "판타지", "competition": "경쟁", "growth": "성장",
        "trust": "신뢰", "safety_net": "안전망", "security_privacy": "보안/개인정보",
        "rewards": "리워드", "savings_benefit": "절약 혜택", "urgency": "긴급성",
        "fun": "재미", "social": "소셜", "convenience": "편의성",
        "curiosity": "호기심", "habit_building": "습관형성", "status_display": "지위표시"
    }
    
    if isinstance(themes, list):
        korean_themes = [theme_map.get(str(theme), str(theme)) for theme in themes]
        return ", ".join(korean_themes) if korean_themes else "N/A"
    else:
        return theme_map.get(str(themes), str(themes)) if themes else "N/A"

def get_korean_motivation_key(key):
    """동기 키를 한국어로 변환"""
    motivation_map = {
        "fun": "재미", "social": "소셜", "rewards": "리워드", "savings": "절약",
        "trust": "신뢰", "convenience": "편의성", "growth": "성장", 
        "status_display": "지위표시", "curiosity": "호기심", 
        "habit_building": "습관형성", "safety_net": "안전망"
    }
    return motivation_map.get(key, key)

def get_korean_engagement_key(key):
    """참여도 키를 한국어로 변환"""
    engagement_map = {
        "casual_score": "캐주얼", "hardcore_score": "하드코어", 
        "frequency_score": "사용빈도", "multi_app_usage": "멀티앱",
        "retention_potential": "유지력", "session_length_expectation": "세션길이"
    }
    return engagement_map.get(key, key)

def get_korean_promo_key(key):
    """프로모션 키를 한국어로 변환"""
    promo_map = {
        "install_reward_sensitive": "설치리워드", "coupon_event_sensitive": "쿠폰이벤트",
        "fomo_sensitive": "FOMO", "exclusive_benefit_sensitive": "독점혜택",
        "trial_experience_sensitive": "체험경험"
    }
    return promo_map.get(key, key)

def get_korean_brand_key(key):
    """브랜드 키를 한국어로 변환"""
    brand_map = {
        "brand_loyalty": "브랜드충성도", "nostalgia": "향수", 
        "trust_in_official": "공식신뢰", "award_proof_sensitive": "수상증명",
        "local_trust_factor": "국내신뢰", "global_trust_factor": "글로벌신뢰"
    }
    return brand_map.get(key, key)

def get_korean_commerce_key(key):
    """상거래 키를 한국어로 변환"""
    commerce_map = {
        "price_sensitivity": "가격민감도", "premium_willingness": "프리미엄지불의향",
        "transaction_frequency": "거래빈도", "risk_tolerance": "위험감수성",
        "recurring_payment": "정기결제", "big_purchase_intent": "고액구매의도"
    }
    return commerce_map.get(key, key)

# =========================================================
# CSV 변환 함수
# =========================================================
def convert_to_csv_format(result: Dict[str, Any]) -> str:
    """JSON 결과를 CSV 형태로 변환합니다."""
    import io
    import csv
    
    # CSV 헤더 정의 (json_total.csv 구조와 동일)
    headers = [
        'ad_type', 'ad_type_category', 'ad_theme', 'target_age', 'target_gender', 'notes',
        'ads_idx', 'ads_code', 'original_ads_name',
        'motivation_fun', 'motivation_social', 'motivation_rewards', 'motivation_savings',
        'motivation_trust', 'motivation_convenience', 'motivation_growth', 'motivation_status_display',
        'motivation_curiosity', 'motivation_habit_building', 'motivation_safety_net',
        'engagement_casual_score', 'engagement_hardcore_score', 'engagement_frequency_score',
        'engagement_multi_app_usage', 'engagement_retention_potential', 'engagement_session_length_expectation',
        'promo_install_reward_sensitive', 'promo_coupon_event_sensitive', 'promo_fomo_sensitive',
        'promo_exclusive_benefit_sensitive', 'promo_trial_experience_sensitive',
        'brand_brand_loyalty', 'brand_nostalgia', 'brand_trust_in_official', 'brand_award_proof_sensitive',
        'brand_local_trust_factor', 'brand_global_trust_factor',
        'commerce_price_sensitivity', 'commerce_premium_willingness', 'commerce_transaction_frequency',
        'commerce_risk_tolerance', 'commerce_recurring_payment', 'commerce_big_purchase_intent'
    ]
    
    # 데이터 추출
    row_data = []
    
    # 기본 정보
    row_data.extend([
        result.get('ad_type', ''),
        ','.join(result.get('ad_type_category', [])),
        ','.join(result.get('ad_theme', [])),
        result.get('target_age', ''),
        result.get('target_gender', ''),
        ','.join(result.get('notes', [])),
        result.get('ads_idx', ''),
        result.get('ads_code', ''),
        result.get('ads_name', '')
    ])
    
    # Motivation
    motivation = result.get('motivation', {})
    row_data.extend([
        motivation.get('fun', 0),
        motivation.get('social', 0),
        motivation.get('rewards', 0),
        motivation.get('savings', 0),
        motivation.get('trust', 0),
        motivation.get('convenience', 0),
        motivation.get('growth', 0),
        motivation.get('status_display', 0),
        motivation.get('curiosity', 0),
        motivation.get('habit_building', 0),
        motivation.get('safety_net', 0)
    ])
    
    # Engagement
    engagement = result.get('engagement', {})
    row_data.extend([
        engagement.get('casual_score', 0),
        engagement.get('hardcore_score', 0),
        engagement.get('frequency_score', 0),
        engagement.get('multi_app_usage', 0),
        engagement.get('retention_potential', 0),
        engagement.get('session_length_expectation', '')
    ])
    
    # Promo
    promo = result.get('promo', {})
    row_data.extend([
        promo.get('install_reward_sensitive', 0),
        promo.get('coupon_event_sensitive', 0),
        promo.get('fomo_sensitive', 0),
        promo.get('exclusive_benefit_sensitive', 0),
        promo.get('trial_experience_sensitive', 0)
    ])
    
    # Brand
    brand = result.get('brand', {})
    row_data.extend([
        brand.get('brand_loyalty', 0),
        brand.get('nostalgia', 0),
        brand.get('trust_in_official', 0),
        brand.get('award_proof_sensitive', 0),
        brand.get('local_trust_factor', 0),
        brand.get('global_trust_factor', 0)
    ])
    
    # Commerce
    commerce = result.get('commerce', {})
    row_data.extend([
        commerce.get('price_sensitivity', 0),
        commerce.get('premium_willingness', 0),
        commerce.get('transaction_frequency', 0),
        commerce.get('risk_tolerance', 0),
        commerce.get('recurring_payment', 0),
        commerce.get('big_purchase_intent', 0)
    ])
    
    # CSV 생성
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(row_data)
    
    return output.getvalue()

# =========================================================
# 광고 분류 함수
# =========================================================
def classify_ad(ad_data: Dict[str, str], api_key: str) -> Optional[Dict[str, Any]]:
    """광고 데이터를 분류합니다."""
    ad_text = f"""
광고명: {ad_data.get('ads_name', '')}
요약: {ad_data.get('ads_summary', '')}
가이드: {ad_data.get('ads_guide', '')}
제한사항: {ad_data.get('ads_limit', '')}
리워드 가격: {ad_data.get('ads_reward_price', '')}
연령 범위: {ad_data.get('ads_age_min', '')}~{ad_data.get('ads_age_max', '')}
시작일: {ad_data.get('ads_sdate', '')}
종료일: {ad_data.get('ads_edate', '')}
사용자 지정 광고 유형: {ad_data.get('ad_type', '')}
사용자 지정 광고 카테고리: {ad_data.get('ad_type_category', '')}
""".strip()

    prompt = create_classification_prompt() + "\n\n" + "광고 텍스트:\n" + ad_text
    result = call_gemini_json(prompt, api_key=api_key)
    
    if result is None:
        return None

    # 원본 데이터 추가
    result["ads_idx"] = ad_data.get("ads_idx", "")
    result["ads_code"] = ad_data.get("ads_code", "")
    result["ads_name"] = ad_data.get("ads_name", "")
    result["ads_summary"] = ad_data.get("ads_summary", "")
    result["ads_guide"] = ad_data.get("ads_guide", "")
    result["ads_limit"] = ad_data.get("ads_limit", "")
    result["ads_reward_price"] = ad_data.get("ads_reward_price", "")
    result["ads_age_min"] = ad_data.get("ads_age_min", "")
    result["ads_age_max"] = ad_data.get("ads_age_max", "")
    result["ads_sdate"] = ad_data.get("ads_sdate", "")
    result["ads_edate"] = ad_data.get("ads_edate", "")
    
    return result

# =========================================================
# Streamlit UI
# =========================================================
def main():
    st.set_page_config(
        page_title="IVE 광고 분류기",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 IVE 광고 분류기")
    st.markdown("---")
    
    # 데이터 구조 설명 섹션
    with st.expander("📋 json_total.csv 테이블 구조 설명", expanded=False):
        st.markdown("""
        ### 📊 분류 결과 데이터 구조 (json_total.csv)
        
        **핵심 원칙**: 명시적 키워드가 없더라도, 광고 유형(ad_type)과 문맥을 바탕으로 관련성이 높은 항목에 대해서는 0 대신 합리적인 기본 점수(예: 0.2~0.5)를 적극적으로 부여함
        
        #### 기본 분류 정보
        - **ad_type**: 게임 → game, 앱(유틸, 카메라, 소셜 등) → app, 쇼핑몰, 이커머스 → shopping, 금융, 보험, 증권, 가상화폐 → finance, 배달, 부동산, 구인구직, 데이팅 등 서비스 → service, 스트리밍, 웹툰, VOD → content, 헬스케어/병원/건강관리 → healthcare, 교육/강의/학습 → education, 리워드 전용 앱 → rewards_only, 기타 → other
        - **ad_type_category**: 상위 유형에 따라 선택된 정보
        - **ad_theme**: 서사·정서·소구 포인트 태깅, 복수 가능
        - **target_age**: 명시 있으면 그대로 반영 (예: 13~18세 → teens) 성인이면 19세 이상임으로 → adults 단서 없으면 → all_ages 연령 범위 보고 유추 가능 보험, 금융 → 기본 thirties 이상 추정 가능
        - **target_gender**: 명시 없으면 기본 neutral, 여성용 뷰티/패션 강조 → female_focus, 아니면 female 남성 전용 서비스(면도, 밀리터리) → male_focus, 아니면 male
        - **notes**: guide에 중요 표인트 tagging
        - **ads_idx**: 광고 고유 번호
        - **ads_code**: ads_idx가 다르더라도 ads_code가 같으면 유저는 그 중 1가지 광고에만 참여할 수 있다.
        - **original_ads_name**: 광고 이름 ads_name과 동일
        
        #### 🎯 동기 (Motivation) - 0.0 ~ 1.0 점수
        사용자가 광고에 반응하는 심리적 동기를 분석합니다:
        
        - **motivation_fun (재미)**: 게임이나 엔터테인먼트 요소에 대한 관심도
          - 게임 광고는 명시적 단어 없어도 기본 0.7 이상 부여
          - 엔터테인먼트, 콘텐츠 유형도 0.3 이상 추론
          
        - **motivation_social (소셜)**: 친구들과 공유하거나 소통하고 싶은 욕구
          - 소셜 네트워킹, 커뮤니티 관련 광고에서 높은 점수
          
        - **motivation_rewards (리워드)**: 포인트나 혜택을 받고 싶은 욕구
          - '적립', '보상' 언급 시 1.0
          - 쇼핑, 게임 유형 광고는 문맥상 암시만 있어도 0.3 이상 추론
          
        - **motivation_savings (절약)**: 돈을 절약하고 싶은 욕구
          - '할인', '최저가' 언급 시 1.0
          - 쇼핑 유형 광고는 가격 소구 가능성이 높으므로 기본 0.3 이상 추론
          
        - **motivation_trust (신뢰)**: 안전하고 신뢰할 수 있는 서비스에 대한 선호
          - 금융, 헬스케어 광고는 신뢰가 중요하므로 기본 0.5 이상 부여
          - '공식', '인증' 등 언급 시 1.0
          
        - **motivation_convenience (편의성)**: 간편하고 쉬운 사용에 대한 선호
          - 편의 관련 기능이나 서비스 광고에서 높은 점수
          
        - **motivation_growth (성장)**: 개인적 발전이나 학습에 대한 욕구
          - 교육, 게임(특히 RPG) 유형은 성장 요소가 내재되어 있으므로 기본 0.4 이상 추론
          
        - **motivation_status_display (지위표시)**: 사회적 지위나 인정받고 싶은 욕구
          - 명품, 고급 서비스, 성취감을 주는 광고에서 높은 점수
          
        - **motivation_curiosity (호기심)**: 새로운 것을 탐험하고 싶은 욕구
          - '무료 체험', '새로운 기능' 등 언급 시 1.0
          - 신규 앱/서비스 광고는 호기심 유발 가능성이 높으므로 0.2 이상 추론
          
        - **motivation_habit_building (습관형성)**: 규칙적인 행동 패턴 형성에 대한 선호
          - 일상생활 개선, 건강 관리, 학습 습관 관련 광고에서 높은 점수
          
        - **motivation_safety_net (안전망)**: 위험을 피하고 안전을 추구하는 욕구
          - 보험, 보안, 안전 관련 서비스 광고에서 높은 점수
        
        #### 🎮 참여도 (Engagement) - 0.0 ~ 1.0 점수
        사용자의 앱 사용 패턴과 참여 수준을 분석합니다:
        
        - **engagement_casual_score (캐주얼)**: 가벼운 앱 사용 선호도
          - 간단한 게임, 뉴스, 날씨 앱 등 가벼운 사용에 적합한 앱
          
        - **engagement_hardcore_score (하드코어)**: 깊이 있는 앱 사용 선호도
          - 복잡한 게임, 전문 도구, 학습 앱 등 깊이 있는 사용이 필요한 앱
          
        - **engagement_frequency_score (사용빈도)**: 자주 사용할 앱에 대한 선호도
          - 일상적으로 자주 사용하는 앱에 대한 관심도
          
        - **engagement_multi_app_usage (멀티앱)**: 여러 앱을 동시에 사용하는 성향
          - 0: 단일 앱 집중 사용, 1: 여러 앱 동시 사용 선호
          
        - **engagement_retention_potential (유지력)**: 오래 사용할 앱에 대한 선호도
          - 장기적으로 사용할 수 있는 앱에 대한 관심도
          
        - **engagement_session_length_expectation (세션길이)**: 앱 사용 시간 기대치
          - 'short': 짧은 시간 사용 (5분 이하)
          - 'medium': 중간 시간 사용 (5-30분)
          - 'long': 긴 시간 사용 (30분 이상)
        
        #### 🎁 프로모션 (Promotion) - 0.0 ~ 1.0 점수
        다양한 프로모션 요소에 대한 반응도를 분석합니다:
        
        - **promo_install_reward_sensitive (설치리워드)**: 앱 설치 시 리워드에 대한 민감도
          - 앱 설치만으로도 포인트나 혜택을 받을 수 있는 광고에서 높은 점수
          
        - **promo_coupon_event_sensitive (쿠폰이벤트)**: 쿠폰이나 이벤트에 대한 민감도
          - 할인 쿠폰, 특별 이벤트, 한정 혜택 등에 대한 반응도
          
        - **promo_fomo_sensitive (FOMO)**: 놓칠 수 있다는 불안감에 대한 민감도
          - '한정 시간', '선착순', '마감 임박' 등 시간적 압박감을 주는 광고
          
        - **promo_exclusive_benefit_sensitive (독점혜택)**: 특별한 혜택에 대한 민감도
          - VIP 혜택, 회원 전용, 특별 할인 등 독점적인 혜택에 대한 반응도
          
        - **promo_trial_experience_sensitive (체험경험)**: 무료 체험이나 샘플에 대한 민감도
          - 무료 체험, 샘플 제공, 테스트 기회 등에 대한 관심도
        
        #### 🏢 브랜드 (Brand) - 0.0 ~ 1.0 점수
        브랜드에 대한 인식과 신뢰도를 분석합니다:
        
        - **brand_brand_loyalty (브랜드충성도)**: 특정 브랜드에 대한 충성도
          - 브랜드 로고, 슬로건, 브랜드 스토리 등에 대한 반응도
          
        - **brand_nostalgia (향수)**: 과거에 대한 그리움이나 추억에 대한 반응
          - 레트로, 클래식, 추억을 자극하는 요소들에 대한 감정적 반응
          
        - **brand_trust_in_official (공식신뢰)**: 공식 채널이나 인증된 서비스에 대한 신뢰
          - 공식 인증, 정식 출시, 공식 파트너십 등에 대한 신뢰도
          
        - **brand_award_proof_sensitive (수상증명)**: 수상 경력이나 인증에 대한 민감도
          - 상장, 인증서, 수상 내역 등 권위 있는 증명에 대한 반응도
          
        - **brand_local_trust_factor (국내신뢰)**: 한국 내에서의 신뢰도
          - 국내 브랜드, 한국어 서비스, 국내 시장에서의 인지도
          
        - **brand_global_trust_factor (글로벌신뢰)**: 해외에서의 신뢰도
          - 글로벌 브랜드, 해외 진출, 국제적 인지도에 대한 반응도
        
        #### 💰 상거래 (Commerce) - 0.0 ~ 1.0 점수
        구매 행동과 금전적 성향을 분석합니다:
        
        - **commerce_price_sensitivity (가격민감도)**: 가격에 대한 민감도
          - 할인, 가격 비교, 저렴한 가격에 대한 반응도
          
        - **commerce_premium_willingness (프리미엄지불의향)**: 고급 서비스에 대한 지불 의향
          - 프리미엄 서비스, 고급 기능, 품질에 대한 지불 의향도
          
        - **commerce_transaction_frequency (거래빈도)**: 자주 구매하는 성향
          - 반복 구매, 정기적 구매, 자주 사용하는 서비스에 대한 선호도
          
        - **commerce_risk_tolerance (위험감수성)**: 금전적 위험을 감수하는 성향
          - 투자, 새로운 서비스 시도, 불확실한 구매에 대한 위험 감수도
          
        - **commerce_recurring_payment (정기결제)**: 구독형 서비스에 대한 선호도
          - 월 구독, 정기 결제, 구독 모델에 대한 관심도
          
        - **commerce_big_purchase_intent (고액구매의도)**: 큰 금액을 지출할 의도
          - 고가 상품, 대형 구매, 큰 투자에 대한 의향도
        """)
    
    # API 키는 환경변수에서 자동으로 가져옴
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        st.info("💡 Streamlit Secrets 또는 환경변수에서 API 키를 설정해주세요.")
        st.code("""
# Streamlit Secrets 사용 시 (.streamlit/secrets.toml)
GEMINI_API_KEY = "your_api_key_here"

# 또는 환경변수로 설정
export GEMINI_API_KEY="your_api_key_here"
        """)
        st.stop()
    
    # 광고 정보 입력 폼
    st.header("📝 광고 정보 입력")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ads_idx = st.text_input("광고 IDX", placeholder="광고 IDX를 입력하세요")
        ads_code = st.text_input("광고 코드", placeholder="광고 코드를 입력하세요")
        ads_name = st.text_input("광고명", placeholder="광고 이름을 입력하세요")
        ads_reward_price = st.text_input("리워드 가격", placeholder="리워드 가격을 입력하세요")
        ads_age_min = st.number_input("최소 연령", min_value=0, max_value=100, value=0)
        ads_age_max = st.number_input("최대 연령", min_value=0, max_value=100, value=100)
    
    with col2:
        ads_summary = st.text_area("요약", placeholder="광고 요약을 입력하세요", height=100)
        ads_guide = st.text_area("가이드", placeholder="광고 가이드를 입력하세요", height=100)
        ads_limit = st.text_area("제한사항", placeholder="광고 제한사항을 입력하세요", height=100)
        ads_sdate = st.date_input("시작일")
        ads_edate = st.date_input("종료일")
    
    # 광고 타입 및 카테고리 입력 (선택사항)
    st.subheader("🎯 광고 분류 정보 (선택사항)")
    st.info("💡 이 정보를 입력하면 더 정확한 분류가 가능합니다. 비워두면 AI가 자동으로 분석합니다.")
    
    col3, col4 = st.columns(2)
    
    with col3:
        # 광고 타입 선택
        ad_type_options = [
            "", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"
        ]
        ad_type_labels = [
            "자동 분석", "1:설치형", "2:실행형", "3:참여형", "4:클릭형", "5:페북", 
            "6:트위터", "7:인스타", "8:노출형", "9:퀘스트", "10:유튜브", "11:네이버", "12:CPS(물건구매)"
        ]
        ad_type_mapping = dict(zip(ad_type_labels, ad_type_options))
        selected_ad_type_label = st.selectbox("광고 유형", ad_type_labels)
        selected_ad_type = ad_type_mapping[selected_ad_type_label]
    
    with col4:
        # 광고 카테고리 선택
        category_options = [
            "", "0", "1", "2", "3", "4", "5", "6", "7", "8", "10", "11", "12", "13"
        ]
        category_labels = [
            "자동 분석", "0: 카테고리 선택안함", "1: 앱(간편적립)", "2: 경험하기(게임적립)/앱(간편적립) - cpi,cpe", 
            "3: 구독(간편적립)", "4: 간편미션-퀴즈(간편적립)", "5: 경험하기(게임적립) - cpa", 
            "6: 멀티보상(게임적립)", "7: 금융(참여적립)", "8: 무료참여(참여적립)", 
            "10: 유료참여(참여적립)", "11: 쇼핑-상품별카테고리(쇼핑적립)", "12: 제휴몰(쇼핑적립)", "13: 간편미션(간편적립)"
        ]
        category_mapping = dict(zip(category_labels, category_options))
        selected_category_label = st.selectbox("광고 카테고리", category_labels)
        ad_type_category = category_mapping[selected_category_label]
    
    # 분류 실행 버튼
    if st.button("🚀 광고 분류하기", type="primary"):
        if not ads_name.strip():
            st.error("광고명을 입력해주세요.")
        else:
            # 광고 데이터 구성
            ad_data = {
                "ads_idx": ads_idx,
                "ads_code": ads_code,
                "ads_name": ads_name,
                "ads_summary": ads_summary,
                "ads_guide": ads_guide,
                "ads_limit": ads_limit,
                "ads_reward_price": ads_reward_price,
                "ads_age_min": str(ads_age_min),
                "ads_age_max": str(ads_age_max),
                "ads_sdate": str(ads_sdate),
                "ads_edate": str(ads_edate),
                "ad_type": selected_ad_type,
                "ad_type_category": ad_type_category
            }
            
            # 진행 표시
            with st.spinner("광고를 분류하고 있습니다..."):
                result = classify_ad(ad_data, api_key)
            
            if result:
                st.success("✅ 분류가 완료되었습니다!")
                
                # 결과 표시
                st.header("📊 분류 결과")
                
                # 기본 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    # 타겟 연령을 한국어로 표시
                    target_age = result.get("target_age", "N/A")
                    target_age_korean = get_korean_target_age(target_age)
                    st.metric("타겟 연령", target_age_korean)
                    
                    # 광고 유형을 한국어로 표시
                    ad_type = result.get("ad_type", "N/A")
                    ad_type_korean = get_korean_ad_type(ad_type)
                    st.metric("광고 유형", ad_type_korean)
                    
                with col2:
                    # 타겟 성별을 한국어로 표시
                    target_gender = result.get("target_gender", "N/A")
                    target_gender_korean = get_korean_target_gender(target_gender)
                    st.metric("타겟 성별", target_gender_korean)
                    
                    # 카테고리를 한국어로 표시
                    categories = result.get("ad_type_category", [])
                    categories_korean = get_korean_categories(categories)
                    st.metric("카테고리", categories_korean)
                    
                with col3:
                    # 테마를 한국어로 표시
                    themes = result.get("ad_theme", [])
                    themes_korean = get_korean_themes(themes)
                    st.metric("테마", themes_korean)
                
                # 상세 결과를 탭으로 표시
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 동기", "🎮 참여도", "🎁 프로모션", "🏢 브랜드", "💰 상거래"])
                
                with tab1:
                    st.subheader("🎯 동기")
                    motivation = result.get("motivation", {})
                    for key, value in motivation.items():
                        korean_key = get_korean_motivation_key(key)
                        if isinstance(value, (int, float)):
                            st.metric(korean_key, f"{value:.3f}")
                        else:
                            st.write(f"**{korean_key}**: {value}")
                
                with tab2:
                    st.subheader("🎮 참여도")
                    engagement = result.get("engagement", {})
                    for key, value in engagement.items():
                        korean_key = get_korean_engagement_key(key)
                        if isinstance(value, (int, float)):
                            st.metric(korean_key, f"{value:.3f}")
                        else:
                            st.write(f"**{korean_key}**: {value}")
                
                with tab3:
                    st.subheader("🎁 프로모션")
                    promo = result.get("promo", {})
                    for key, value in promo.items():
                        korean_key = get_korean_promo_key(key)
                        if isinstance(value, (int, float)):
                            st.metric(korean_key, f"{value:.3f}")
                        else:
                            st.write(f"**{korean_key}**: {value}")
                
                with tab4:
                    st.subheader("🏢 브랜드")
                    brand = result.get("brand", {})
                    for key, value in brand.items():
                        korean_key = get_korean_brand_key(key)
                        if isinstance(value, (int, float)):
                            st.metric(korean_key, f"{value:.3f}")
                        else:
                            st.write(f"**{korean_key}**: {value}")
                
                with tab5:
                    st.subheader("💰 상거래")
                    commerce = result.get("commerce", {})
                    for key, value in commerce.items():
                        korean_key = get_korean_commerce_key(key)
                        if isinstance(value, (int, float)):
                            st.metric(korean_key, f"{value:.3f}")
                        else:
                            st.write(f"**{korean_key}**: {value}")
                
                # JSON 결과 다운로드
                st.header("💾 결과 다운로드")
                
                # CSV 형태로도 다운로드 가능하도록 데이터 변환
                csv_data = convert_to_csv_format(result)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    json_str = json.dumps(result, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📄 JSON 파일 다운로드",
                        data=json_str,
                        file_name=f"ad_classification_{ads_name.replace(' ', '_')}.json",
                        mime="application/json"
                    )
                
                with col2:
                    st.download_button(
                        label="📊 CSV 파일 다운로드",
                        data=csv_data,
                        file_name=f"ad_classification_{ads_name.replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
                
                # 원본 JSON 표시
                with st.expander("🔍 원본 JSON 결과 보기"):
                    st.json(result)
                
            else:
                st.error("❌ 분류에 실패했습니다. API 키와 입력 정보를 확인해주세요.")

if __name__ == "__main__":
    main()
