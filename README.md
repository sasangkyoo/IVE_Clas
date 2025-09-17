# 📊 IVE 광고 분류기 Streamlit 앱

이 앱은 Google Gemini API를 사용하여 광고 텍스트를 분석하고 사전 정의된 스키마에 따라 분류하는 웹 애플리케이션입니다. 원본 `ad_classifier.py`와 동일한 분류 로직을 사용하지만, 웹 인터페이스를 통해 더 쉽게 사용할 수 있습니다.

## 🚀 주요 기능

- **인터랙티브 입력**: 웹 폼을 통해 광고 정보를 직접 입력
- **실시간 분류**: Google Gemini API를 사용한 AI 기반 광고 분류
- **사용자 지정 분류**: 광고 유형과 카테고리를 미리 지정하여 더 정확한 분류 가능
- **상세한 결과 표시**: 동기, 참여도, 프로모션, 브랜드, 상거래 등 다양한 측면에서 분석
- **결과 다운로드**: JSON 및 CSV 형태로 분류 결과 다운로드 가능
- **상세한 데이터 구조 설명**: json_total.csv 테이블 구조에 대한 완전한 설명 포함
- **사용자 친화적 UI**: Streamlit 기반의 직관적인 웹 인터페이스

## 📋 분류 스키마

### 기본 분류
- **광고 유형 (ad_type)**: 1:설치형, 2:실행형, 3:참여형, 4:클릭형, 5:페북, 6:트위터, 7:인스타, 8:노출형, 9:퀘스트, 10:유튜브, 11:네이버, 12:CPS(물건구매)
- **광고 카테고리 (ad_type_category)**: 0:카테고리선택안함, 1:앱(간편적립), 2:경험하기(게임적립)/앱(간편적립), 3:구독(간편적립), 4:간편미션-퀴즈(간편적립), 5:경험하기(게임적립), 6:멀티보상(게임적립), 7:금융(참여적립), 8:무료참여(참여적립), 10:유료참여(참여적립), 11:쇼핑-상품별카테고리(쇼핑적립), 12:제휴몰(쇼핑적립), 13:간편미션(간편적립)
- **광고 테마 (ad_theme)**: 서사, 정서, 소구 포인트 태깅
- **타겟 연령 (target_age)**: teens, twenties, thirties, forties, fifties, all_ages
- **타겟 성별 (target_gender)**: male_focus, female_focus, neutral

### 🏷️ 광고 타입 및 카테고리 매핑

#### **광고 타입 (12개)**
- **1**: 설치형
- **2**: 실행형
- **3**: 참여형
- **4**: 클릭형
- **5**: 페북
- **6**: 트위터
- **7**: 인스타
- **8**: 노출형
- **9**: 퀘스트
- **10**: 유튜브
- **11**: 네이버
- **12**: CPS(물건구매)

#### **광고 카테고리 (13개)**
- **0**: 카테고리 선택안함
- **1**: 앱(간편적립)
- **2**: 경험하기(게임적립)/앱(간편적립) - cpi,cpe
- **3**: 구독(간편적립)
- **4**: 간편미션-퀘즈(간편적립)
- **5**: 경험하기(게임적립) - cpa
- **6**: 멀티보상(게임적립)
- **7**: 금융(참여적립)
- **8**: 무료참여(참여적립)
- **10**: 유료참여(참여적립)
- **11**: 쇼핑-상품별카테고리(쇼핑적립)
- **12**: 제휴몰(쇼핑적립)
- **13**: 간편미션(간편적립)

### 상세 분석
- **동기 (Motivation)**: fun, social, rewards, savings, trust, convenience, growth, status_display, curiosity, habit_building, safety_net
- **참여도 (Engagement)**: casual_score, hardcore_score, frequency_score, multi_app_usage, retention_potential, session_length_expectation
- **프로모션 (Promo)**: install_reward_sensitive, coupon_event_sensitive, fomo_sensitive, exclusive_benefit_sensitive, trial_experience_sensitive
- **브랜드 (Brand)**: brand_loyalty, nostalgia, trust_in_official, award_proof_sensitive, local_trust_factor, global_trust_factor
- **상거래 (Commerce)**: price_sensitivity, premium_willingness, transaction_frequency, risk_tolerance, recurring_payment, big_purchase_intent

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. API 키 설정
다음 중 하나의 방법으로 Gemini API 키를 설정하세요:

#### 방법 1: Streamlit Secrets 사용 (권장)
`.streamlit/secrets.toml` 파일을 생성하고:
```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
```

#### 방법 2: 환경변수 사용
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

#### 방법 3: .env 파일 사용
`.env` 파일을 생성하고:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 앱 실행
```bash
streamlit run app.py
```

## 📖 사용 방법

1. **광고 정보 입력**: 
   - 광고명 (필수)
   - 요약, 가이드, 제한사항
   - 리워드 가격
   - 연령 범위 (최소/최대)
   - 시작일/종료일
2. **광고 분류 정보 입력 (선택사항)**:
   - 광고 유형: 드롭다운에서 선택 (자동 분석, 1:설치형, 2:실행형, 3:참여형 등)
   - 광고 카테고리: 드롭다운에서 선택 (자동 분석, 0:카테고리선택안함, 1:앱(간편적립) 등)
3. **분류 실행**: "광고 분류하기" 버튼을 클릭하세요
4. **결과 확인**: 분류 결과를 다양한 탭에서 확인할 수 있습니다
5. **결과 다운로드**: JSON 및 CSV 파일로 결과를 다운로드할 수 있습니다

## 🔧 기술 스택

- **프론트엔드**: Streamlit
- **AI API**: Google Gemini 1.5 Flash 8B
- **백엔드**: Python
- **의존성**: requests, python-dotenv

## 📁 파일 구조

```
IVE_Clas/
├── app.py              # 메인 Streamlit 애플리케이션
├── requirements.txt    # Python 의존성
├── README.md          # 프로젝트 문서
└── .env               # 환경 변수 (사용자가 생성)
```

## ⚠️ 주의사항

- Gemini API 키가 필요합니다
- 인터넷 연결이 필요합니다
- API 사용량에 따라 비용이 발생할 수 있습니다

## 🔄 원본 스크립트와의 차이점

이 Streamlit 앱은 원본 `ad_classifier.py` 스크립트와 동일한 분류 로직을 사용하지만, 다음과 같은 차이점이 있습니다:

- **입력 방식**: CSV 파일 대신 웹 폼을 통한 직접 입력
- **처리 방식**: 배치 처리 대신 단일 광고 실시간 처리
- **결과 표시**: JSON 파일 저장 대신 웹 UI에서 시각적 표시
- **다운로드 옵션**: JSON과 CSV 두 가지 형태로 결과 다운로드 가능
- **데이터 구조 설명**: 앱 내에서 json_total.csv 테이블 구조에 대한 상세한 설명 제공
- **사용자 경험**: 명령줄 인터페이스 대신 웹 기반 인터페이스

## 📞 지원

문제가 발생하거나 개선 사항이 있으시면 이슈를 등록해주세요.
