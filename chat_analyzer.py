"""
채팅 분석 엔진
Claude를 활용한 필터 매칭률 계산 및 전체 분석 프로세스 관리
"""

from typing import List, Dict, Any
from tqdm import tqdm
from data_manager import DataManager
from llm_client import ClaudeClient


class ChatAnalyzer:
    """채팅 데이터 분석을 담당하는 메인 클래스"""
    
    def __init__(self, model: str = "claude-3-haiku-20240307"):
        """
        채팅 분석기 초기화
        
        Args:
            model: 사용할 Claude 모델명
        """
        self.data_manager = DataManager()
        self.claude_client = ClaudeClient(model=model)
        self.analysis_results = []
    
    def analyze_csv_file(self, csv_path: str, filter_criteria: str, 
                        window_size: int = 100, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        CSV 파일을 분석하여 필터 매칭률 계산
        
        Args:
            csv_path: CSV 파일 경로
            filter_criteria: 필터 조건
            window_size: 윈도우 크기 (기본값: 100)
            overlap: 겹치는 메시지 수 (기본값: 50)
        
        Returns:
            분석 결과 리스트
        """
        print(f"🚀 채팅 데이터 분석 시작")
        print(f"📁 파일: {csv_path}")
        print(f"🔍 필터: {filter_criteria}")
        print(f"📊 윈도우 크기: {window_size}, 겹침: {overlap}")
        print("-" * 50)
        
        # 1. CSV 파일 로드
        chat_data = self.data_manager.load_csv(csv_path)
        if not chat_data:
            print("❌ CSV 파일 로드 실패")
            return []
        
        # 2. 슬라이딩 윈도우로 분할
        chat_blocks = self.data_manager.create_sliding_windows(window_size, overlap)
        if not chat_blocks:
            print("❌ 채팅 블록 생성 실패")
            return []
        
        # 3. 비용 예상치 출력
        estimated_cost = self._estimate_cost(chat_blocks, filter_criteria)
        print(f"💰 예상 비용: ${estimated_cost['total_usd']:.4f} (₩{estimated_cost['total_krw']:.0f})")
        print(f"📊 예상 토큰: {estimated_cost['estimated_tokens']:,}개")
        
        proceed = input("계속 진행하시겠습니까? (y/N): ").lower().strip()
        if proceed != 'y':
            print("분석이 취소되었습니다.")
            return []
        
        # 4. 각 블록별 매칭률 계산
        print(f"🤖 Claude를 이용한 매칭률 계산 시작...")
        results = []
        
        with tqdm(total=len(chat_blocks), desc="분석 진행") as pbar:
            for i, block in enumerate(chat_blocks):
                try:
                    # Claude로 매칭률 계산 (비용 정보 포함)
                    match_rate, cost_info = self.claude_client.calculate_filter_match_rate(block, filter_criteria)
                    
                    # 결과 저장
                    result = {
                        "block_id": i + 1,
                        "start_index": i * (window_size - overlap),
                        "end_index": min(i * (window_size - overlap) + window_size, len(chat_data)),
                        "message_count": len(block),
                        "match_rate": match_rate,
                        "filter_criteria": filter_criteria,
                        "cost_info": cost_info,
                        "first_message": {
                            "date": block[0]['date'],
                            "user": block[0]['user'],
                            "message": block[0]['message'][:100] + "..." if len(block[0]['message']) > 100 else block[0]['message']
                        },
                        "last_message": {
                            "date": block[-1]['date'],
                            "user": block[-1]['user'],
                            "message": block[-1]['message'][:100] + "..." if len(block[-1]['message']) > 100 else block[-1]['message']
                        }
                    }
                    results.append(result)
                    
                    # 진행상황 업데이트 (매칭률과 누적 비용 표시)
                    current_cost = self.claude_client.total_cost
                    pbar.set_postfix({
                        "매칭률": f"{match_rate:.1f}%", 
                        "누적비용": f"${current_cost:.4f}"
                    })
                    pbar.update(1)
                    
                    # 주기적으로 비용 정보 출력
                    if (i + 1) % 20 == 0:
                        usage = self.claude_client.get_usage_summary()
                        print(f"\n💰 진행상황: {i+1}/{len(chat_blocks)} 완료, "
                              f"비용: ${usage['total_cost_usd']:.4f} (₩{usage['total_cost_krw']:.0f})")
                    
                except Exception as e:
                    print(f"블록 {i+1} 분석 중 오류: {e}")
                    pbar.update(1)
                    continue
        
        self.analysis_results = results
        
        # 5. 최종 통계 및 비용 출력
        self._print_analysis_summary(results)
        self.claude_client.print_usage_summary()
        
        return results
    
    def save_results(self, file_path: str = None) -> str:
        """분석 결과 저장"""
        if not self.analysis_results:
            print("❌ 저장할 분석 결과가 없습니다.")
            return ""
        
        return self.data_manager.save_analysis_results(self.analysis_results, file_path)
    
    def load_results(self, file_path: str) -> List[Dict[str, Any]]:
        """저장된 분석 결과 로드"""
        results = self.data_manager.load_analysis_results(file_path)
        self.analysis_results = results
        return results
    
    def get_blocks_above_threshold(self, threshold: float) -> List[Dict[str, Any]]:
        """임계값 이상의 블록들 반환"""
        if not self.analysis_results:
            print("❌ 분석 결과가 없습니다.")
            return []
        
        filtered_blocks = self.data_manager.filter_by_threshold(self.analysis_results, threshold)
        
        print(f"\n📋 매칭률 {threshold}% 이상인 블록들:")
        print("-" * 50)
        
        for block in filtered_blocks:
            print(f"블록 #{block['block_id']}: {block['match_rate']:.1f}%")
            print(f"  📅 기간: {block['first_message']['date']} ~ {block['last_message']['date']}")
            print(f"  💬 메시지 수: {block['message_count']}개")
            print(f"  🔸 첫 메시지: [{block['first_message']['user']}] {block['first_message']['message']}")
            print(f"  🔹 마지막 메시지: [{block['last_message']['user']}] {block['last_message']['message']}")
            print("-" * 50)
        
        return filtered_blocks
    
    def _print_analysis_summary(self, results: List[Dict[str, Any]]):
        """분석 결과 요약 출력"""
        if not results:
            return
        
        stats = self.data_manager.get_statistics(results)
        
        print(f"\n📊 분석 결과 요약")
        print("=" * 50)
        print(f"전체 블록 수: {stats['total_blocks']}개")
        print(f"평균 매칭률: {stats['average_match_rate']:.1f}%")
        print(f"최고 매칭률: {stats['max_match_rate']:.1f}%")
        print(f"최저 매칭률: {stats['min_match_rate']:.1f}%")
        print(f"50% 이상 블록: {stats['blocks_above_50']}개")
        print(f"75% 이상 블록: {stats['blocks_above_75']}개")
        print("=" * 50)
    
    def get_detailed_block_info(self, block_id: int) -> Dict[str, Any]:
        """특정 블록의 상세 정보 반환"""
        if not self.analysis_results:
            print("❌ 분석 결과가 없습니다.")
            return {}
        
        for result in self.analysis_results:
            if result['block_id'] == block_id:
                return result
        
        print(f"❌ 블록 #{block_id}를 찾을 수 없습니다.")
        return {}
    
    def _estimate_cost(self, chat_blocks: List[List[Dict[str, str]]], filter_criteria: str) -> Dict[str, Any]:
        """비용 추정"""
        # 샘플 블록으로 평균 토큰 수 계산
        sample_block = chat_blocks[0] if chat_blocks else []
        sample_text = self.claude_client._format_chat_messages(sample_block)
        sample_prompt = self.claude_client._create_analysis_prompt(sample_text, filter_criteria)
        
        # 대략적인 토큰 수 계산 (영어 기준 4글자 = 1토큰, 한국어는 더 많이 소모)
        estimated_input_tokens_per_block = len(sample_prompt) // 3  # 한국어 고려하여 보수적으로 계산
        estimated_output_tokens_per_block = 50  # max_tokens 설정값
        
        total_blocks = len(chat_blocks)
        total_input_tokens = estimated_input_tokens_per_block * total_blocks
        total_output_tokens = estimated_output_tokens_per_block * total_blocks
        
        # 비용 계산
        if self.claude_client.model in self.claude_client.MODEL_PRICING:
            pricing = self.claude_client.MODEL_PRICING[self.claude_client.model]
            input_cost = (total_input_tokens / 1000) * pricing["input"]
            output_cost = (total_output_tokens / 1000) * pricing["output"]
            total_cost_usd = input_cost + output_cost
        else:
            total_cost_usd = 0.0
        
        return {
            "total_blocks": total_blocks,
            "estimated_tokens": total_input_tokens + total_output_tokens,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "total_usd": total_cost_usd,
            "total_krw": total_cost_usd * 1350,
            "model": self.claude_client.model
        }
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """현재 세션의 비용 요약 반환"""
        return self.claude_client.get_usage_summary()