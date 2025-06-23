"""
Anthropic Claude API 클라이언트 모듈
채팅 데이터의 필터 매칭률을 계산하기 위한 LLM 인터페이스
"""

import os
from typing import List, Dict, Any
from anthropic import Anthropic
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class ClaudeClient:
    """Anthropic Claude API 클라이언트"""
    
    def __init__(self, model: str = "claude-3-haiku-20240307"):
        """
        Claude 클라이언트 초기화
        
        Args:
            model: 사용할 Claude 모델명 (기본값: claude-3-haiku-20240307)
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def calculate_filter_match_rate(self, chat_messages: List[Dict[str, str]], filter_criteria: str) -> float:
        """
        채팅 메시지들이 필터 조건에 얼마나 부합하는지 계산
        
        Args:
            chat_messages: 채팅 메시지 리스트 [{"date": "...", "user": "...", "message": "..."}]
            filter_criteria: 필터 조건 (예: "긍정적인 대화", "업무 관련 내용" 등)
        
        Returns:
            0-100 사이의 매칭률 (float)
        """
        # 채팅 메시지를 텍스트로 변환
        chat_text = self._format_chat_messages(chat_messages)
        
        # 프롬프트 생성
        prompt = self._create_analysis_prompt(chat_text, filter_criteria)
        
        try:
            # Claude API 호출
            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 응답에서 점수 추출
            score = self._extract_score(response.content[0].text)
            return score
            
        except Exception as e:
            print(f"Claude API 호출 중 오류 발생: {e}")
            return 0.0
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """채팅 메시지를 분석용 텍스트로 포맷팅"""
        formatted_lines = []
        for msg in messages:
            date = msg.get('date', '').strip()
            user = msg.get('user', '').strip()
            message = msg.get('message', '').strip()
            
            if message:  # 빈 메시지는 제외
                formatted_lines.append(f"[{date}] {user}: {message}")
        
        return "\n".join(formatted_lines)
    
    def _create_analysis_prompt(self, chat_text: str, filter_criteria: str) -> str:
        """필터 매칭률 분석을 위한 프롬프트 생성"""
        return f"""다음 채팅 대화를 분석하고, 주어진 필터 조건에 얼마나 부합하는지 0-100 사이의 점수로 평가해주세요.

필터 조건: {filter_criteria}

채팅 내용:
{chat_text}

평가 기준:
- 0점: 필터 조건과 전혀 관련 없음
- 25점: 약간 관련 있음
- 50점: 보통 수준으로 관련 있음
- 75점: 많이 관련 있음
- 100점: 완전히 필터 조건에 부합함

답변은 숫자만 입력해주세요 (예: 75)"""
    
    def _extract_score(self, response_text: str) -> float:
        """Claude 응답에서 점수 추출"""
        import re
        
        # 숫자 패턴 찾기
        numbers = re.findall(r'\d+', response_text)
        
        if numbers:
            score = float(numbers[0])
            # 0-100 범위로 제한
            return max(0.0, min(100.0, score))
        
        return 0.0
    
    def batch_analyze(self, chat_blocks: List[List[Dict[str, str]]], filter_criteria: str) -> List[float]:
        """
        여러 채팅 블록을 일괄 분석
        
        Args:
            chat_blocks: 채팅 블록들의 리스트
            filter_criteria: 필터 조건
        
        Returns:
            각 블록의 매칭률 리스트
        """
        results = []
        
        for i, block in enumerate(chat_blocks):
            print(f"블록 {i+1}/{len(chat_blocks)} 분석 중...")
            score = self.calculate_filter_match_rate(block, filter_criteria)
            results.append(score)
        
        return results