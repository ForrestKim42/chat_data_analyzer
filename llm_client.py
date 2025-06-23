"""
Anthropic Claude API 클라이언트 모듈
채팅 데이터의 필터 매칭률을 계산하기 위한 LLM 인터페이스
"""

import os
from typing import List, Dict, Any, Tuple
from anthropic import Anthropic
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class ClaudeClient:
    """Anthropic Claude API 클라이언트"""
    
    # 모델별 가격 정보 (1K 토큰당 USD)
    MODEL_PRICING = {
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
    }
    
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
        
        # 비용 추적 변수
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
    
    def calculate_filter_match_rate(self, chat_messages: List[Dict[str, str]], filter_criteria: str) -> Tuple[float, Dict[str, Any]]:
        """
        채팅 메시지들이 필터 조건에 얼마나 부합하는지 계산
        
        Args:
            chat_messages: 채팅 메시지 리스트 [{"date": "...", "user": "...", "message": "..."}]
            filter_criteria: 필터 조건 (예: "긍정적인 대화", "업무 관련 내용" 등)
        
        Returns:
            (매칭률, 비용정보) 튜플
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
            
            # 토큰 사용량 및 비용 계산
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost_info = self._calculate_cost(input_tokens, output_tokens)
            
            # 누적 통계 업데이트
            self._update_usage_stats(input_tokens, output_tokens, cost_info['request_cost'])
            
            # 응답에서 점수 추출
            score = self._extract_score(response.content[0].text)
            
            return score, cost_info
            
        except Exception as e:
            print(f"Claude API 호출 중 오류 발생: {e}")
            return 0.0, {"request_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
    
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
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """토큰 사용량을 기반으로 비용 계산"""
        if self.model not in self.MODEL_PRICING:
            return {
                "request_cost": 0.0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "model": self.model
            }
        
        pricing = self.MODEL_PRICING[self.model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "request_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "model": self.model
        }
    
    def _update_usage_stats(self, input_tokens: int, output_tokens: int, cost: float):
        """사용량 통계 업데이트"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.request_count += 1
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """현재까지의 사용량 요약 반환"""
        return {
            "total_requests": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": self.total_cost,
            "total_cost_krw": self.total_cost * 1350,  # 대략적인 환율
            "average_cost_per_request": self.total_cost / max(1, self.request_count),
            "model": self.model
        }
    
    def print_usage_summary(self):
        """사용량 요약을 콘솔에 출력"""
        summary = self.get_usage_summary()
        print(f"\n💰 API 사용량 요약")
        print("=" * 40)
        print(f"모델: {summary['model']}")
        print(f"총 요청 수: {summary['total_requests']:,}회")
        print(f"입력 토큰: {summary['total_input_tokens']:,}개")
        print(f"출력 토큰: {summary['total_output_tokens']:,}개")
        print(f"총 토큰: {summary['total_tokens']:,}개")
        print(f"총 비용: ${summary['total_cost_usd']:.4f} (약 ₩{summary['total_cost_krw']:.0f})")
        print(f"요청당 평균 비용: ${summary['average_cost_per_request']:.4f}")
        print("=" * 40)
    
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
            score, cost_info = self.calculate_filter_match_rate(block, filter_criteria)
            results.append(score)
            
            # 실시간 비용 정보 출력
            if i % 10 == 0:  # 10번마다 출력
                print(f"💰 현재까지 비용: ${self.total_cost:.4f} (₩{self.total_cost * 1350:.0f})")
        
        return results