#!/bin/bash

# 채팅 데이터 분석기 환경 설정 스크립트

echo "🚀 채팅 데이터 분석기 환경 설정을 시작합니다..."

# Python 가상환경 생성
echo "📦 가상환경 생성 중..."
python3 -m venv venv

# 가상환경 활성화
echo "🔄 가상환경 활성화 중..."
source venv/bin/activate

# 패키지 설치
echo "📥 필요한 패키지 설치 중..."
pip install --upgrade pip
pip install -r requirements.txt

# .env 파일 생성 (API 키 설정용)
if [ ! -f .env ]; then
    echo "🔑 환경 변수 파일 생성 중..."
    cat > .env << EOF
# Anthropic Claude API 키를 입력하세요
ANTHROPIC_API_KEY=your_api_key_here
EOF
    echo "⚠️  .env 파일이 생성되었습니다. ANTHROPIC_API_KEY를 설정해주세요."
fi

echo "✅ 환경 설정이 완료되었습니다!"
echo ""
echo "🔧 사용 방법:"
echo "1. .env 파일에 ANTHROPIC_API_KEY 설정"
echo "2. source venv/bin/activate (가상환경 활성화)"
echo "3. python main.py (프로그램 실행)"
echo ""
echo "💡 다음에 실행할 때는 'source activate.sh'만 실행하세요."