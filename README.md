# 대동세무고 교육과정 관리 시스템

대동세무고등학교 교육과정 편성 및 교원 수급 분석을 위한 웹 애플리케이션

## 주요 기능

| 탭 | 기능 |
|---|---|
| 📅 연도별 운영 현황 | 학년도별 실제 운영 과목·학점을 학년/학과별로 한눈에 확인 |
| 📚 교육과정 편성표 | 입학년도별 교육과정 편성 현황 (1학기/2학기 분리) |
| 👩‍🏫 교사 수급 분석 | 교과별 수업시수·교사 배치 현황, 시수 과부족 경고 |
| 🔄 상치교과 관리 | 수기 편집 가능한 상치교과 배정표, 학년도별 메모 저장 |
| 🗺️ 2027 편성 가이드 | 기존 교육과정 기반 예측 + 편성 체크리스트 |

## 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 실행
streamlit run app.py
```

## Streamlit Cloud 배포

1. 이 레포를 GitHub에 push
2. [share.streamlit.io](https://share.streamlit.io) → New app
3. 레포: `raykel0512-ai/daedong-curriculum`
4. Branch: `main`, File: `app.py`
5. Deploy

## 데이터 업데이트

### 방법 A: 파일 업로드 (매년 갱신 시)
앱 사이드바에서 엑셀 파일 두 개를 직접 업로드 → 파싱 버튼

### 방법 B: JSON 갱신 (기본 데이터 변경 시)
`data/curriculum_data.json` 파일을 새로 생성해서 GitHub에 push

## 파일 구조

```
daedong-curriculum/
├── app.py                  # 메인 Streamlit 앱
├── parser.py               # 엑셀 파싱 모듈
├── storage.py              # 편집 데이터 저장/불러오기
├── requirements.txt
├── .streamlit/
│   └── config.toml         # 테마 설정
└── data/
    ├── curriculum_data.json  # 기본 파싱 데이터 (GitHub에 포함)
    └── edits.json            # 수기 편집 저장 (gitignore)
```

## 교과배정표 컬럼 구조

단위배당표 열 배치:
- col7/9: 1학년 공통 1학기/2학기
- col11~22: 2학년 (세무회계/관세무역/세무행정) × 1·2학기
- col23~34: 3학년 동일 구조
