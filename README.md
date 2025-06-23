# 채팅 데이터 분석기

Claude AI를 활용하여 CSV 형식의 채팅 데이터를 분석하고, 사용자가 정의한 필터 조건에 대한 매칭률을 계산하는 도구입니다.

## 주요 기능

- 📊 CSV 파일 (Date,User,Message 형식) 읽기
- 🔄 슬라이딩 윈도우 방식으로 채팅 분할 (100개씩, 50개 겹침)
- 🤖 Claude AI를 활용한 필터 매칭률 계산
- 💰 **실시간 비용 추적 및 예상 비용 계산**
- 💾 분석 결과 저장 및 로드
- 🔍 임계값 기반 채팅 블록 검색
- 📈 분석 결과 통계 제공

## 설치 및 설정

### 1. 환경 설정

```bash
# 자동 설정 스크립트 실행
./setup.sh

# 또는 수동 설정
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. API 키 설정

`.env` 파일을 생성하고 Anthropic API 키를 추가하세요:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. 가상환경 활성화

```bash
# 다음 실행시에는 이 명령어만 사용
source activate.sh
```

## 사용법

### 💰 비용 추정 (분석 전 필수!)

```bash
# 분석 전 예상 비용 확인
python main.py estimate chat.csv "긍정적인 대화"

# 모델별 가격 정보 확인
python main.py pricing
```

### 🤖 기본 분석

```bash
python main.py analyze chat.csv "긍정적인 대화"
```

### ⚙️ 옵션 사용

```bash
python main.py analyze chat.csv "업무 관련 대화" \
    --window-size 150 \
    --overlap 75 \
    --model claude-3-haiku-20240307 \
    --output my_analysis.json
```

### 🔍 결과 검색

```bash
# 75% 이상 매칭률을 가진 블록 검색
python main.py search analysis_results_20240623_143022.json 75
```

### 📊 통계 확인

```bash
python main.py stats analysis_results_20240623_143022.json
```

### 🔍 블록 상세 정보

```bash
python main.py detail analysis_results_20240623_143022.json 5
```

### 🛠️ 설정 가이드

```bash
python main.py setup
```

## 명령어 상세

### estimate
분석 전 예상 비용을 계산합니다. **분석 실행 전 반드시 확인하세요!**

**사용법:**
```bash
python main.py estimate [옵션] CSV_파일 필터_조건
```

### pricing  
모델별 가격 정보를 출력합니다.

**사용법:**
```bash
python main.py pricing
```

### analyze
CSV 파일을 분석하여 필터 매칭률을 계산합니다. **실시간 비용 추적 포함**

**사용법:**
```bash
python main.py analyze [옵션] CSV_파일 필터_조건
```

**옵션:**
- `--window-size, -w`: 채팅 윈도우 크기 (기본값: 100)
- `--overlap, -o`: 윈도우 겹침 크기 (기본값: 50)
- `--model, -m`: 사용할 Claude 모델 (기본값: claude-3-haiku-20240307)
- `--output, -out`: 결과 저장 파일명

**비용 추적 기능:**
- 분석 시작 전 예상 비용 표시 및 확인 요청
- 실시간 누적 비용 표시 (20블록마다)
- 최종 완료 후 상세 비용 요약

### search
저장된 분석 결과에서 임계값 이상의 블록들을 검색합니다.

**사용법:**
```bash
python main.py search 결과_파일 임계값
```

### stats
저장된 분석 결과의 통계를 출력합니다.

**사용법:**
```bash
python main.py stats 결과_파일
```

### detail
특정 블록의 상세 정보를 출력합니다.

**사용법:**
```bash
python main.py detail 결과_파일 블록_ID
```

## CSV 파일 형식

입력 CSV 파일은 다음 형식이어야 합니다:

```csv
Date,User,Message
2024-06-23 14:30:22,사용자1,안녕하세요
2024-06-23 14:30:35,사용자2,반갑습니다
2024-06-23 14:31:10,사용자1,오늘 날씨가 좋네요
```

## 필터 조건 예시

- "긍정적인 대화"
- "업무 관련 내용"
- "감정적인 표현이 포함된 대화"
- "질문과 답변이 오가는 대화"
- "특정 주제에 대한 토론"

## 출력 결과

분석 결과는 JSON 형식으로 저장되며, 다음 정보를 포함합니다:

- 블록 ID 및 인덱스 범위
- 매칭률 (0-100%)
- 메시지 수
- 첫 번째/마지막 메시지 정보
- 필터 조건

## 파일 구조

```
chat_data_analyzer/
├── main.py              # 메인 실행 파일
├── chat_analyzer.py     # 채팅 분석 엔진
├── llm_client.py        # Claude API 클라이언트
├── data_manager.py      # 데이터 관리 모듈
├── requirements.txt     # 의존성 패키지
├── setup.sh            # 환경 설정 스크립트
├── activate.sh         # 가상환경 활성화 스크립트
├── .env               # 환경 변수 (API 키)
├── .gitignore         # Git 무시 파일
└── README.md          # 사용 설명서
```

## 💰 비용 관리

### 모델별 가격 (1K 토큰당)
- **claude-3-haiku-20240307**: 입력 $0.00025, 출력 $0.00125 ⭐ 추천 (가장 저렴)
- **claude-3-5-haiku-20241022**: 입력 $0.001, 출력 $0.005 
- **claude-3-5-sonnet-20240620**: 입력 $0.003, 출력 $0.015 (성능 균형)
- **claude-3-sonnet-20240229**: 입력 $0.003, 출력 $0.015
- **claude-3-opus-20240229**: 입력 $0.015, 출력 $0.075 (가장 비쌈)

### 비용 절약 팁
1. **필수**: 분석 전 `python main.py estimate` 실행
2. Haiku 모델 사용 (가장 저렴하고 빠름)
3. 윈도우 크기 조정으로 블록 수 최적화
4. 작은 샘플로 테스트 후 전체 분석 진행

### 예상 비용 예시
- **1,000개 메시지** (10블록): 약 $0.01-0.05 (₩15-70)
- **10,000개 메시지** (100블록): 약 $0.10-0.50 (₩135-675)
- **100,000개 메시지** (1,000블록): 약 $1-5 (₩1,350-6,750)

## 주의사항

- **💰 분석 전 반드시 비용 추정을 확인하세요**
- API 키는 `.env` 파일에 안전하게 보관하세요
- 입력 CSV 파일과 분석 결과는 Git에 업로드되지 않습니다
- Claude API 사용량에 따라 비용이 발생할 수 있습니다
- 대용량 파일 분석 시 시간이 오래 걸릴 수 있습니다

## 문제 해결

### API 키 오류
```
❌ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.
```
→ `.env` 파일에 올바른 API 키를 설정하세요.

### CSV 파일 형식 오류
```
❌ CSV 파일에 필요한 컬럼이 없습니다.
```
→ Date,User,Message 형식의 CSV 파일을 사용하세요.

### 메모리 부족
큰 파일의 경우 윈도우 크기를 줄이거나 여러 번에 나누어 처리하세요.