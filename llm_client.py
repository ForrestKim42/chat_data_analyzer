"""
최적화된 Anthropic Claude API 클라이언트 모듈
병렬 처리, 연결 풀, 재시도 로직, 캐싱으로 성능 향상
"""

import os
import time
import hashlib
import json
import asyncio
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from anthropic import Anthropic
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class OptimizedClaudeClient:
    """성능 최적화된 Anthropic Claude API 클라이언트"""
    
    # 모델별 가격 정보 (1K 토큰당 USD)
    MODEL_PRICING = {
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-5-sonnet-20240620": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
    }
    
    def __init__(self, model: str = "claude-3-haiku-20240307", max_workers: int = 5, 
                 enable_cache: bool = True, max_retries: int = 3):
        """
        최적화된 Claude 클라이언트 초기화
        
        Args:
            model: 사용할 Claude 모델명
            max_workers: 병렬 처리 워커 수
            enable_cache: 캐싱 활성화 여부
            max_retries: 최대 재시도 횟수
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_workers = max_workers
        self.max_retries = max_retries
        
        # 성능 최적화 설정
        self.enable_cache = enable_cache
        self.cache = {} if enable_cache else None
        self.cache_lock = threading.Lock()
        
        # 비용 추적 변수 (스레드 안전)
        self.stats_lock = threading.Lock()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        self.failed_requests = 0
        self.rate_limit_count = 0
        
        # 성능 측정
        self.start_time = None
        self.request_times = []
    
    def calculate_filter_match_rate_single(self, chat_messages: List[Dict[str, str]], 
                                         filter_criteria: str) -> Tuple[float, Dict[str, Any]]:
        """
        단일 채팅 블록의 필터 매칭률 계산 (스레드 안전)
        """
        # 캐시 키 생성
        cache_key = None
        if self.enable_cache:
            cache_key = self._generate_cache_key(chat_messages, filter_criteria)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        # 채팅 메시지를 텍스트로 변환
        chat_text = self._format_chat_messages(chat_messages)
        
        # 최적화된 프롬프트 생성
        prompt = self._create_optimized_prompt(chat_text, filter_criteria)
        
        # 재시도 로직으로 API 호출
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Claude API 호출
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=80,  # 점수와 요약을 위해 증가
                    temperature=0.0,  # 일관성을 위해 0으로 설정
                    messages=[{"role": "user", "content": prompt}]
                )
                
                request_time = time.time() - start_time
                
                # 토큰 사용량 및 비용 계산
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost_info = self._calculate_cost(input_tokens, output_tokens)
                
                # 누적 통계 업데이트 (스레드 안전)
                self._update_usage_stats(input_tokens, output_tokens, 
                                       cost_info['request_cost'], request_time)
                
                # 응답에서 점수와 요약 추출
                score, summary = self._extract_score_and_summary(response.content[0].text)
                
                # 비용 정보에 요약 추가
                cost_info['summary'] = summary
                result = (score, cost_info)
                
                # 캐시에 저장
                if self.enable_cache and cache_key:
                    self._save_to_cache(cache_key, result)
                
                return result
                
            except Exception as e:
                error_msg = self._format_error_message(e)
                
                # 429 에러 카운트
                if "429" in str(e) or "rate_limit_exceeded" in str(e).lower():
                    with self.stats_lock:
                        self.rate_limit_count += 1
                
                if attempt == self.max_retries - 1:
                    print(f"❌ API 호출 실패 (최대 재시도 초과): {error_msg}")
                    with self.stats_lock:
                        self.failed_requests += 1
                    return 0.0, {"request_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
                
                # 429 에러의 경우 더 긴 대기시간
                if "429" in str(e) or "rate_limit_exceeded" in str(e).lower():
                    wait_time = (2 ** attempt) * 2 + (time.time() % 1)  # 더 긴 대기
                    if attempt == 0:
                        print(f"⏳ API 사용량 한도 초과 - 대기 후 재시도합니다...")
                else:
                    wait_time = (2 ** attempt) + (time.time() % 1)
                
                if attempt < self.max_retries - 1:  # 마지막 시도가 아닐 때만 메시지 출력
                    print(f"⚠️ 재시도 {attempt + 1}/{self.max_retries} ({wait_time:.1f}초 대기): {error_msg}")
                time.sleep(wait_time)
        
        return 0.0, {"request_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
    
    def batch_analyze_parallel(self, chat_blocks: List[List[Dict[str, str]]], 
                             filter_criteria: str, 
                             progress_callback=None) -> List[Tuple[float, Dict[str, Any]]]:
        """
        병렬 처리로 여러 채팅 블록을 일괄 분석
        
        Args:
            chat_blocks: 채팅 블록들의 리스트
            filter_criteria: 필터 조건
            progress_callback: 진행상황 콜백 함수
        
        Returns:
            (매칭률, 비용정보) 튜플들의 리스트
        """
        self.start_time = time.time()
        results = [None] * len(chat_blocks)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업을 병렬로 제출
            future_to_index = {
                executor.submit(self.calculate_filter_match_rate_single, block, filter_criteria): i
                for i, block in enumerate(chat_blocks)
            }
            
            completed = 0
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    completed += 1
                    
                    # 진행상황 콜백 호출
                    if progress_callback:
                        progress_callback(completed, len(chat_blocks), result[0])
                        
                except Exception as e:
                    error_msg = self._format_error_message(e)
                    print(f"❌ 블록 {index + 1} 처리 중 오류: {error_msg}")
                    results[index] = (0.0, {"request_cost": 0.0, "input_tokens": 0, "output_tokens": 0})
                    completed += 1
                    
                    if progress_callback:
                        progress_callback(completed, len(chat_blocks), 0.0)
        
        return results
    
    def _generate_cache_key(self, chat_messages: List[Dict[str, str]], filter_criteria: str) -> str:
        """캐시 키 생성"""
        content = json.dumps(chat_messages, sort_keys=True) + filter_criteria + self.model
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Tuple[float, Dict[str, Any]]:
        """캐시에서 결과 조회"""
        if not self.enable_cache:
            return None
            
        with self.cache_lock:
            return self.cache.get(cache_key)
    
    def _save_to_cache(self, cache_key: str, result: Tuple[float, Dict[str, Any]]):
        """캐시에 결과 저장"""
        if not self.enable_cache:
            return
            
        with self.cache_lock:
            self.cache[cache_key] = result
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """채팅 메시지를 분석용 텍스트로 포맷팅 (최적화)"""
        formatted_lines = []
        for msg in messages:
            message = msg.get('message', '').strip()
            user = msg.get('user', '').strip()
            
            if message:  # 빈 메시지는 제외
                # 간결한 형태로 포맷팅 (토큰 절약)
                formatted_lines.append(f"{user}: {message}")
        
        return "\n".join(formatted_lines)
    
    def _create_optimized_prompt(self, chat_text: str, filter_criteria: str) -> str:
        """최적화된 프롬프트 생성 (토큰 절약)"""
        return f"""채팅 분석: "{filter_criteria}" 조건에 대한 매칭도를 0-100 정수 점수로 평가하고 대화 내용을 한줄로 요약하세요.

채팅:
{chat_text}

평가기준:
- 0-20: 전혀 관련 없음
- 21-40: 약간 관련 있음
- 41-60: 보통 관련 있음  
- 61-80: 많이 관련 있음
- 81-100: 매우 관련 있음

응답 형식:
점수: [0-100 정수]
요약: [대화 내용을 간단히 한줄로 요약]

예시:
점수: 67
요약: 김선태와 허진영이 프로젝트 일정과 업무 분담에 대해 논의함"""
    
    def _extract_score_and_summary(self, response_text: str) -> tuple[float, str]:
        """Claude 응답에서 점수와 요약 추출"""
        import re
        
        score = 0.0
        summary = "분석 불가"
        
        # 점수 추출 패턴
        score_patterns = [
            r'점수[:\s]*(\d+)',  # "점수: 67" 형태
            r'(\d+)\s*점',  # "67점" 형태
            r'(\d+)\s*%',  # "67%" 형태
            r'score[:\s]*(\d+)',  # "score: 67" 형태 (영어)
            r'(\d+)'  # 기본 숫자 (마지막 시도)
        ]
        
        # 요약 추출 패턴
        summary_patterns = [
            r'요약[:\s]*(.+?)(?:\n|$)',  # "요약: 내용" 형태
            r'summary[:\s]*(.+?)(?:\n|$)',  # "summary: 내용" 형태 (영어)
            r'(?:점수[:\s]*\d+\s*\n?)(.+?)(?:\n|$)',  # 점수 다음 줄
        ]
        
        # 점수 추출
        for pattern in score_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            if matches:
                try:
                    score = float(matches[0])
                    score = max(0.0, min(100.0, score))
                    break
                except ValueError:
                    continue
        
        # 요약 추출
        for pattern in summary_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if matches:
                summary = matches[0].strip()
                # 너무 긴 요약은 잘라내기
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                break
        
        # 요약이 너무 짧거나 의미없으면 기본값
        if len(summary) < 5 or summary.lower() in ['none', 'n/a', '-']:
            if score >= 80:
                summary = "매우 높은 관련성"
            elif score >= 60:
                summary = "높은 관련성"
            elif score >= 40:
                summary = "보통 관련성"
            elif score >= 20:
                summary = "낮은 관련성"
            else:
                summary = "관련성 없음"
        
        return score, summary
    
    def _extract_score(self, response_text: str) -> float:
        """하위 호환성을 위한 기존 함수 (점수만 추출)"""
        score, _ = self._extract_score_and_summary(response_text)
        return score
    
    def _format_error_message(self, error: Exception) -> str:
        """에러 메시지를 사용자 친화적으로 포맷팅"""
        error_str = str(error)
        
        # 429 Rate Limit 에러
        if "429" in error_str or "rate_limit_exceeded" in error_str.lower():
            return "⏳ API 사용량 한도 초과 (잠시 후 재시도)"
        
        # 401 인증 에러
        if "401" in error_str or "unauthorized" in error_str.lower():
            return "🔑 API 키 인증 실패 (API 키를 확인해주세요)"
        
        # 403 권한 에러
        if "403" in error_str or "forbidden" in error_str.lower():
            return "🚫 API 접근 권한 없음"
        
        # 500 서버 에러
        if "500" in error_str or "internal_server_error" in error_str.lower():
            return "🔧 서버 내부 오류 (잠시 후 재시도)"
        
        # 502, 503, 504 서버 에러
        if any(code in error_str for code in ["502", "503", "504"]):
            return "🔧 서버 일시 장애 (잠시 후 재시도)"
        
        # 연결 에러
        if any(keyword in error_str.lower() for keyword in ["connection", "timeout", "network"]):
            return "🌐 네트워크 연결 문제"
        
        # JSON 파싱 에러
        if "json" in error_str.lower():
            return "📄 응답 형식 오류"
        
        # 기타 에러는 간단하게 표시
        if len(error_str) > 100:
            return f"🔧 API 오류: {error_str[:50]}..."
        
        return f"🔧 API 오류: {error_str}"
    
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
    
    def _update_usage_stats(self, input_tokens: int, output_tokens: int, 
                          cost: float, request_time: float):
        """사용량 통계 업데이트 (스레드 안전)"""
        with self.stats_lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost += cost
            self.request_count += 1
            self.request_times.append(request_time)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        with self.stats_lock:
            total_time = time.time() - self.start_time if self.start_time else 0
            avg_request_time = sum(self.request_times) / len(self.request_times) if self.request_times else 0
            requests_per_second = self.request_count / total_time if total_time > 0 else 0
            
            return {
                "total_requests": self.request_count,
                "failed_requests": self.failed_requests,
                "rate_limit_errors": self.rate_limit_count,
                "success_rate": (self.request_count - self.failed_requests) / max(1, self.request_count) * 100,
                "total_time_seconds": total_time,
                "average_request_time": avg_request_time,
                "requests_per_second": requests_per_second,
                "cache_hits": len(self.cache) if self.enable_cache else 0,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_cost_usd": self.total_cost,
                "total_cost_krw": self.total_cost * 1350,
                "model": self.model,
                "max_workers": self.max_workers
            }
    
    def print_performance_summary(self):
        """성능 요약을 콘솔에 출력"""
        summary = self.get_performance_summary()
        
        print(f"\n🚀 성능 분석 결과")
        print("=" * 50)
        print(f"모델: {summary['model']}")
        print(f"병렬 워커: {summary['max_workers']}개")
        print(f"총 요청: {summary['total_requests']:,}회")
        print(f"실패 요청: {summary['failed_requests']:,}회")
        if summary['rate_limit_errors'] > 0:
            print(f"⏳ 사용량 한도 에러: {summary['rate_limit_errors']:,}회")
        print(f"성공률: {summary['success_rate']:.1f}%")
        print(f"총 처리시간: {summary['total_time_seconds']:.1f}초")
        print(f"평균 요청시간: {summary['average_request_time']:.2f}초")
        print(f"초당 요청수: {summary['requests_per_second']:.1f} req/s")
        if self.enable_cache:
            print(f"캐시 항목: {summary['cache_hits']:,}개")
        print(f"총 토큰: {summary['total_input_tokens'] + summary['total_output_tokens']:,}개")
        print(f"총 비용: ${summary['total_cost_usd']:.4f} (₩{summary['total_cost_krw']:.0f})")
        
        # 429 에러가 많으면 조언 제공
        if summary['rate_limit_errors'] > summary['total_requests'] * 0.1:  # 10% 이상
            print("\n💡 사용량 한도 에러가 자주 발생했습니다:")
            print("   • --workers 옵션으로 병렬 워커 수를 줄여보세요 (예: --workers 2)")
            print("   • 더 작은 단위로 나누어 분석해보세요")
            print("   • Anthropic API 요금제 업그레이드를 고려해보세요")
        
        print("=" * 50)