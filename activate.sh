#!/bin/bash

# 채팅 데이터 분석기 가상환경 활성화 스크립트

if [ ! -d "venv" ]; then
    echo "❌ 가상환경이 없습니다. 먼저 './setup.sh'를 실행하세요."
    exit 1
fi

echo "🔄 가상환경 활성화 중..."
source venv/bin/activate

echo "✅ 가상환경이 활성화되었습니다!"
echo "💡 프로그램 실행: python main.py"