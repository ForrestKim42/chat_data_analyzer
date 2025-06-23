"""
채팅 분석 엔진
병렬 처리, 캐싱, 스마트 배치로 성능 향상
"""

import time
from typing import List, Dict, Any
from tqdm import tqdm
from data_manager import DataManager
from llm_client import OptimizedClaudeClient


class ChatAnalyzer:
    """채팅 데이터 분석 클래스"""
    
    def __init__(self, model: str = "claude-3-haiku-20240307", 
                 max_workers: int = 3, enable_cache: bool = True):
        """
        채팅 분석기 초기화
        
        Args:
            model: 사용할 Claude 모델명
            max_workers: 병렬 처리 워커 수 (기본값: 5)
            enable_cache: 캐싱 활성화 여부 (기본값: True)
        """
        self.data_manager = DataManager()
        self.claude_client = OptimizedClaudeClient(
            model=model, 
            max_workers=max_workers, 
            enable_cache=enable_cache
        )
        self.analysis_results = []
        
        # 성능 설정
        self.max_workers = max_workers
        self.enable_cache = enable_cache
    
    def analyze_csv_file(self, csv_path: str, filter_criteria: str, 
                        window_size: int = 100, overlap: int = 50,
                        fast_mode: bool = True, recent_days: int = None) -> List[Dict[str, Any]]:
        """
        최적화된 CSV 파일 분석
        
        Args:
            csv_path: CSV 파일 경로
            filter_criteria: 필터 조건
            window_size: 윈도우 크기
            overlap: 겹치는 메시지 수
            fast_mode: 고속 모드 (더 작은 샘플링과 병렬 처리)
            recent_days: 최근 N일 이내 데이터만 분석 (None이면 전체)
        
        Returns:
            분석 결과 리스트
        """
        print(f"🚀 채팅 데이터 분석 시작")
        print(f"📁 파일: {csv_path}")
        print(f"🔍 필터: {filter_criteria}")
        print(f"📊 윈도우: {window_size}, 겹침: {overlap}")
        if recent_days:
            print(f"📅 기간: 최근 {recent_days}일")
        print(f"⚡ 고속모드: {'활성화' if fast_mode else '비활성화'}")
        print(f"🔧 병렬워커: {self.max_workers}개")
        print(f"💾 캐싱: {'활성화' if self.enable_cache else '비활성화'}")
        print("-" * 60)
        
        # 1. CSV 파일 로드
        chat_data = self.data_manager.load_csv(csv_path, recent_days)
        if not chat_data:
            print("❌ CSV 파일 로드 실패")
            return []
        
        # 2. 슬라이딩 윈도우로 분할
        self.data_manager.chat_data = chat_data  # 업데이트된 데이터 설정
        chat_blocks = self.data_manager.create_sliding_windows(window_size, overlap)
        if not chat_blocks:
            print("❌ 채팅 블록 생성 실패")
            return []
        
        # 3. 비용 예상치 및 시간 예상치 출력
        estimated_cost = self._estimate_cost_and_time(chat_blocks, filter_criteria)
        print(f"💰 예상 비용: ${estimated_cost['total_usd']:.4f} (₩{estimated_cost['total_krw']:.0f})")
        print(f"⏱️ 예상 시간: {estimated_cost['estimated_time']:.1f}초")
        print(f"📊 처리 블록: {len(chat_blocks):,}개")
        
        # 4. 대용량 데이터 추가 경고 (비용 확인 후)
        if fast_mode and len(chat_data) > 50000:
            print(f"\n⚠️  대용량 데이터 분석: {len(chat_data):,}개 메시지")
            print(f"💡 완료까지 시간이 걸릴 수 있습니다.")
        
        proceed = input("\n분석을 시작하시겠습니까? (y/N): ").lower().strip()
        if proceed != 'y':
            print("분석이 취소되었습니다.")
            return []
        
        # 5. 병렬 분석 실행
        print(f"🤖 병렬 분석 시작 ({self.max_workers}개 워커)...")
        
        # 진행률 표시를 위한 tqdm 설정
        progress_bar = tqdm(total=len(chat_blocks), desc="분석 진행", 
                          bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} '
                                   '[⏱️{elapsed}<⏲️{remaining}, 🚀{rate_fmt}, 💰${postfix}]')
        
        def progress_callback(completed, total, latest_score):
            current_cost = self.claude_client.total_cost
            progress_bar.set_postfix_str(f"{current_cost:.4f}")
            progress_bar.n = completed
            progress_bar.refresh()
        
        # 병렬 분석 실행
        start_time = time.time()
        parallel_results = self.claude_client.batch_analyze_parallel(
            chat_blocks, filter_criteria, progress_callback
        )
        progress_bar.close()
        
        # 6. 결과 정리
        results = []
        for i, (match_rate, cost_info) in enumerate(parallel_results):
            result = {
                "block_id": i + 1,
                "start_index": i * (window_size - overlap),
                "end_index": min(i * (window_size - overlap) + window_size, len(chat_data)),
                "message_count": len(chat_blocks[i]),
                "match_rate": match_rate,
                "summary": cost_info.get('summary', '분석 요약 없음'),
                "filter_criteria": filter_criteria,
                "cost_info": cost_info,
                "first_message": {
                    "date": chat_blocks[i][0]['date'],
                    "user": chat_blocks[i][0]['user'],
                    "message": chat_blocks[i][0]['message'][:100] + "..." if len(chat_blocks[i][0]['message']) > 100 else chat_blocks[i][0]['message']
                },
                "last_message": {
                    "date": chat_blocks[i][-1]['date'],
                    "user": chat_blocks[i][-1]['user'],
                    "message": chat_blocks[i][-1]['message'][:100] + "..." if len(chat_blocks[i][-1]['message']) > 100 else chat_blocks[i][-1]['message']
                }
            }
            results.append(result)
        
        self.analysis_results = results
        
        # 7. 최종 통계 및 성능 출력
        total_time = time.time() - start_time
        self._print_analysis_summary(results)
        self.claude_client.print_performance_summary()
        
        # 8. 비용 예상치 vs 실제 비교
        actual_usage = self.claude_client.get_performance_summary()
        print(f"\n📊 예상 vs 실제 비교")
        print("=" * 40)
        print(f"예상 입력 토큰: {estimated_cost['total_input_tokens']:,}개")
        print(f"실제 입력 토큰: {actual_usage['total_input_tokens']:,}개")
        if estimated_cost['total_input_tokens'] > 0:
            accuracy = (actual_usage['total_input_tokens'] / estimated_cost['total_input_tokens']) * 100
            print(f"예상 정확도: {accuracy:.1f}%")
        
        print(f"예상 시간: {estimated_cost['estimated_time']:.1f}초")
        print(f"실제 시간: {total_time:.1f}초")
        
        print(f"예상 비용: ${estimated_cost['total_usd']:.4f}")
        print(f"실제 비용: ${actual_usage['total_cost_usd']:.4f}")
        print("=" * 40)
        
        print(f"\n⚡ 성능 향상 효과")
        print("=" * 40)
        sequential_time = len(chat_blocks) * 2.0  # 순차 처리 예상 시간
        speedup = sequential_time / total_time if total_time > 0 else 1
        print(f"실제 처리시간: {total_time:.1f}초")
        print(f"순차 처리 예상: {sequential_time:.1f}초")
        print(f"속도 향상: {speedup:.1f}x")
        print("=" * 40)
        
        return results
    
    def save_results(self, file_path: str = None) -> str:
        """분석 결과 저장"""
        if not self.analysis_results:
            print("❌ 저장할 분석 결과가 없습니다.")
            return ""
        
        # 성능 정보도 함께 저장
        for result in self.analysis_results:
            if 'performance_info' not in result:
                result['performance_info'] = self.claude_client.get_performance_summary()
        
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
            print(f"  📝 요약: {block.get('summary', '요약 없음')}")
            print(f"  📅 기간: {block['first_message']['date']} ~ {block['last_message']['date']}")
            print(f"  💬 메시지 수: {block['message_count']}개")
            print(f"  🔸 첫 메시지: [{block['first_message']['user']}] {block['first_message']['message']}")
            print(f"  🔹 마지막 메시지: [{block['last_message']['user']}] {block['last_message']['message']}")
            print("-" * 50)
        
        return filtered_blocks
    
    def _estimate_cost_and_time(self, chat_blocks: List[List[Dict[str, str]]], 
                               filter_criteria: str) -> Dict[str, Any]:
        """비용 및 시간 추정 (개선된 토큰 계산)"""
        
        # 성능과 정확도의 균형을 위한 적응형 샘플링
        total_blocks = len(chat_blocks)
        if total_blocks <= 10:
            # 적은 블록 수면 모든 블록 분석
            sample_size = total_blocks
            print(f"🔍 소규모 데이터: 모든 {total_blocks}개 블록 분석")
        elif total_blocks <= 100:
            # 중간 규모면 10% 샘플링 (최소 5개)
            sample_size = max(5, total_blocks // 10)
            print(f"🔍 중간 규모 데이터: {sample_size}개 블록 샘플링 ({sample_size/total_blocks*100:.1f}%)")
        else:
            # 대규모면 고정 10개 샘플링
            sample_size = 10
            print(f"🔍 대규모 데이터: {sample_size}개 블록 샘플링 ({sample_size/total_blocks*100:.1f}%)")
        
        total_sample_tokens = 0
        
        for i in range(sample_size):
            sample_block = chat_blocks[i]
            sample_text = self.claude_client._format_chat_messages(sample_block)
            sample_prompt = self.claude_client._create_optimized_prompt(sample_text, filter_criteria)
            
            # 더 정확한 토큰 추정 (한국어와 영어 혼재 고려)
            # 한국어: 글자당 1.5토큰, 영어: 단어당 1.3토큰, 공백/기호: 0.5토큰
            korean_chars = sum(1 for char in sample_prompt if '\uac00' <= char <= '\ud7af')
            english_words = len([word for word in sample_prompt.split() if word.isascii() and word.isalpha()])
            other_chars = len(sample_prompt) - korean_chars - sum(len(word) for word in sample_prompt.split() if word.isascii() and word.isalpha())
            
            estimated_tokens = int(korean_chars * 1.5 + english_words * 1.3 + other_chars * 0.5)
            total_sample_tokens += estimated_tokens
        
        # 평균 토큰 수 계산
        avg_input_tokens_per_block = total_sample_tokens // sample_size if sample_size > 0 else 500
        estimated_output_tokens_per_block = 80  # max_tokens 설정값 (점수 + 요약)
        
        total_input_tokens = avg_input_tokens_per_block * total_blocks
        total_output_tokens = estimated_output_tokens_per_block * total_blocks
        
        # 비용 계산
        if self.claude_client.model in self.claude_client.MODEL_PRICING:
            pricing = self.claude_client.MODEL_PRICING[self.claude_client.model]
            input_cost = (total_input_tokens / 1000) * pricing["input"]
            output_cost = (total_output_tokens / 1000) * pricing["output"]
            total_cost_usd = input_cost + output_cost
        else:
            total_cost_usd = 0.0
        
        # 시간 추정 (병렬 처리 고려)
        avg_request_time = 1.5  # 평균 요청 시간 (초)
        parallel_time = (total_blocks / self.max_workers) * avg_request_time
        estimated_time = parallel_time * 1.2  # 오버헤드 고려
        
        # 디버그 정보 출력
        print(f"🔍 비용 계산 세부사항:")
        print(f"  샘플 블록 수: {sample_size}개")
        print(f"  블록당 평균 입력 토큰: {avg_input_tokens_per_block:,}개")
        print(f"  블록당 출력 토큰: {estimated_output_tokens_per_block}개")
        print(f"  총 입력 토큰: {total_input_tokens:,}개")
        print(f"  총 출력 토큰: {total_output_tokens:,}개")
        
        return {
            "total_blocks": total_blocks,
            "estimated_tokens": total_input_tokens + total_output_tokens,
            "avg_input_tokens_per_block": avg_input_tokens_per_block,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_usd": total_cost_usd,
            "total_krw": total_cost_usd * 1350,
            "estimated_time": estimated_time,
            "parallel_workers": self.max_workers,
            "model": self.claude_client.model
        }
    
    def _print_analysis_summary(self, results: List[Dict[str, Any]]):
        """분석 결과 요약 출력"""
        if not results:
            return
        
        stats = self.data_manager.get_statistics(results)
        
        print(f"\n📊 분석 결과 요약")
        print("=" * 50)
        print(f"전체 블록 수: {stats['total_blocks']:,}개")
        print(f"평균 매칭률: {stats['average_match_rate']:.1f}%")
        print(f"최고 매칭률: {stats['max_match_rate']:.1f}%")
        print(f"최저 매칭률: {stats['min_match_rate']:.1f}%")
        print(f"50% 이상 블록: {stats['blocks_above_50']:,}개")
        print(f"75% 이상 블록: {stats['blocks_above_75']:,}개")
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
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 반환"""
        return self.claude_client.get_performance_summary()