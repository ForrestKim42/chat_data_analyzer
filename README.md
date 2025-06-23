# 채팅 데이터 분석기

Claude AI를 활용하여 CSV 형식의 채팅 데이터를 분석하고, 사용자가 정의한 필터 조건에 대한 매칭률을 계산하는 도구입니다.

## 주요 기능

- 📊 CSV 파일 (Date,User,Message 형식) 읽기
- 🔄 슬라이딩 윈도우 방식으로 채팅 분할 (100개씩, 50개 겹침)
- 🤖 Claude AI를 활용한 필터 매칭률 계산
- ⚡ **병렬 처리로 3-5배 빠른 분석**
- 🧠 **스마트 캐싱으로 중복 분석 방지**
- 🔍 **전체 데이터 분석으로 검색 누락 방지**
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

### ⚡ 분석 실행

```bash
python main.py analyze chat.csv "긍정적인 대화"
```

### ⚙️ 옵션 사용

```bash
python main.py analyze chat.csv "업무 관련 대화" \
    --window-size 150 \
    --overlap 75 \
    --model claude-3-haiku-20240307 \
    --workers 8 \
    --recent-days 30 \
    --output my_analysis.json
```

### 📅 최근 데이터만 분석

```bash
# 최근 7일 이내 데이터만 분석
python main.py analyze chat.csv "업무 지시" --recent-days 7

# 최근 30일 이내 데이터만 분석
python main.py estimate chat.csv "긍정적인 대화" --recent-days 30
```

## 성능 최적화 특징

⚡ **병렬 처리**: 5개 워커가 동시에 블록 분석
🧠 **스마트 캐싱**: 동일한 블록 재분석 방지  
🔍 **전체 데이터 분석**: 검색 누락 없이 모든 데이터 처리
📊 **실시간 모니터링**: 진행률과 비용을 실시간 추적
🛡️ **안정성**: 지수 백오프 재시도로 네트워크 오류 복구

## 검색 정확성 보장

❌ **데이터 샘플링 없음**: 모든 채팅 메시지를 빠짐없이 분석
✅ **겹침 윈도우**: 50개씩 겹쳐서 경계 메시지도 놓치지 않음
🎯 **정확한 검색**: 사용자 쿼리에 해당하는 모든 블록 발견

## 명령어 상세

### estimate
분석 전 예상 비용을 계산합니다.

### analyze  
CSV 파일을 병렬 처리로 분석합니다.

**옵션:**
- `--workers`: 병렬 처리 워커 수 (기본값: 5)
- `--recent-days`: 최근 N일 이내 데이터만 분석
- `--no-cache`: 캐싱 비활성화
- `--no-fast`: 대용량 데이터 경고 비활성화

### search
저장된 분석 결과에서 임계값 이상의 블록들을 검색합니다.

### stats
저장된 분석 결과의 통계를 출력합니다.

## 💰 비용 관리

### 모델별 가격 (1K 토큰당)
- **claude-3-haiku-20240307**: 입력 $0.00025, 출력 $0.00125 ⭐ 추천
- **claude-3-5-haiku-20241022**: 입력 $0.001, 출력 $0.005 
- **claude-3-5-sonnet-20240620**: 입력 $0.003, 출력 $0.015

### 비용 절약 팁
1. **필수**: 분석 전 `python main.py estimate` 실행
2. Haiku 모델 사용 (가장 저렴하고 빠름)
3. 작은 샘플로 테스트 후 전체 분석 진행

## CSV 파일 형식

```csv
Date,User,Message
2024-06-23 14:30:22,사용자1,안녕하세요
2024-06-23 14:30:35,사용자2,반갑습니다
```

## 주의사항

- **💰 분석 전 반드시 비용 추정을 확인하세요**
- API 키는 `.env` 파일에 안전하게 보관하세요
- 입력 CSV 파일과 분석 결과는 Git에 업로드되지 않습니다
- 🔍 **모든 데이터를 분석하므로 검색 누락이 없습니다**