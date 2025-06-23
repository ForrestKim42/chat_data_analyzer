#!/usr/bin/env python3
"""
채팅 데이터 분석기 메인 프로그램
CSV 파일의 채팅 데이터를 분석하여 사용자 정의 필터에 매칭되는 정도를 계산
"""

import os
import sys
import click
from chat_analyzer import ChatAnalyzer


@click.group()
def cli():
    """채팅 데이터 분석기 - CSV 파일의 채팅을 AI로 분석합니다."""
    pass


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.argument('filter_criteria', type=str)
@click.option('--window-size', '-w', default=100, help='채팅 윈도우 크기 (기본값: 100)')
@click.option('--overlap', '-o', default=50, help='윈도우 겹침 크기 (기본값: 50)')
@click.option('--model', '-m', default='claude-3-haiku-20240307', help='사용할 Claude 모델')
@click.option('--workers', default=5, help='병렬 처리 워커 수 (기본값: 5)')
@click.option('--no-cache', is_flag=True, help='캐싱 비활성화')
@click.option('--no-fast', is_flag=True, help='대용량 데이터 경고 비활성화')
@click.option('--recent-days', '-d', type=int, help='최근 N일 이내 데이터만 분석')
@click.option('--output', '-out', help='결과 저장 파일명')
def analyze(csv_file, filter_criteria, window_size, overlap, model, workers, no_cache, no_fast, recent_days, output):
    """⚡ CSV 파일을 병렬 처리로 빠르게 분석합니다."""
    
    # API 키 확인
    if not os.getenv('ANTHROPIC_API_KEY'):
        click.echo("❌ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        click.echo("💡 .env 파일에 API 키를 설정하거나 환경 변수로 설정해주세요.")
        sys.exit(1)
    
    try:
        # 분석기 초기화
        from chat_analyzer import ChatAnalyzer
        analyzer = ChatAnalyzer(
            model=model, 
            max_workers=workers, 
            enable_cache=not no_cache
        )
        
        click.echo("🚀 분석을 시작합니다!")
        click.echo(f"🔧 설정: {workers}개 워커, 캐싱 {'OFF' if no_cache else 'ON'}, 대용량경고 {'OFF' if no_fast else 'ON'}")
        
        # 분석 실행
        results = analyzer.analyze_csv_file(
            csv_path=csv_file,
            filter_criteria=filter_criteria,
            window_size=window_size,
            overlap=overlap,
            fast_mode=not no_fast,
            recent_days=recent_days
        )
        
        if not results:
            click.echo("❌ 분석 결과가 없습니다.")
            sys.exit(1)
        
        # 결과 저장
        saved_file = analyzer.save_results(output)
        if saved_file:
            click.echo(f"\n💾 분석 결과가 저장되었습니다: {saved_file}")
            click.echo(f"🔍 임계값 검색을 하려면: python main.py search {saved_file} <임계값>")
            click.echo(f"📊 성능 정보도 함께 저장되었습니다.")
        
    except Exception as e:
        click.echo(f"❌ 분석 중 오류 발생: {e}")
        sys.exit(1)


@cli.command()
@click.argument('result_file', type=click.Path(exists=True))
@click.argument('threshold', type=float)
def search(result_file, threshold):
    """저장된 분석 결과에서 임계값 이상의 블록들을 검색합니다."""
    
    try:
        # 분석기 초기화 및 결과 로드
        analyzer = ChatAnalyzer()
        results = analyzer.load_results(result_file)
        
        if not results:
            click.echo("❌ 분석 결과를 로드할 수 없습니다.")
            sys.exit(1)
        
        # 임계값 이상 블록 검색
        filtered_blocks = analyzer.get_blocks_above_threshold(threshold)
        
        if not filtered_blocks:
            click.echo(f"🔍 매칭률 {threshold}% 이상인 블록이 없습니다.")
        else:
            click.echo(f"\n✅ 총 {len(filtered_blocks)}개의 블록이 {threshold}% 이상의 매칭률을 보입니다.")
        
    except Exception as e:
        click.echo(f"❌ 검색 중 오류 발생: {e}")
        sys.exit(1)


@cli.command()
@click.argument('result_file', type=click.Path(exists=True))
def stats(result_file):
    """저장된 분석 결과의 통계를 출력합니다."""
    
    try:
        # 분석기 초기화 및 결과 로드
        analyzer = ChatAnalyzer()
        results = analyzer.load_results(result_file)
        
        if not results:
            click.echo("❌ 분석 결과를 로드할 수 없습니다.")
            sys.exit(1)
        
        # 통계 출력 (이미 ChatAnalyzer에서 처리됨)
        from data_manager import DataManager
        data_manager = DataManager()
        stats_info = data_manager.get_statistics(results)
        
        click.echo(f"\n📊 분석 결과 통계")
        click.echo("=" * 50)
        click.echo(f"전체 블록 수: {stats_info['total_blocks']}개")
        click.echo(f"평균 매칭률: {stats_info['average_match_rate']:.1f}%")
        click.echo(f"최고 매칭률: {stats_info['max_match_rate']:.1f}%")
        click.echo(f"최저 매칭률: {stats_info['min_match_rate']:.1f}%")
        click.echo(f"50% 이상 블록: {stats_info['blocks_above_50']}개")
        click.echo(f"75% 이상 블록: {stats_info['blocks_above_75']}개")
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ 통계 출력 중 오류 발생: {e}")
        sys.exit(1)


@cli.command()
@click.argument('result_file', type=click.Path(exists=True))
@click.argument('block_id', type=int)
def detail(result_file, block_id):
    """특정 블록의 상세 정보를 출력합니다."""
    
    try:
        # 분석기 초기화 및 결과 로드
        analyzer = ChatAnalyzer()
        results = analyzer.load_results(result_file)
        
        if not results:
            click.echo("❌ 분석 결과를 로드할 수 없습니다.")
            sys.exit(1)
        
        # 블록 상세 정보 출력
        block_info = analyzer.get_detailed_block_info(block_id)
        
        if not block_info:
            click.echo(f"❌ 블록 #{block_id}를 찾을 수 없습니다.")
            sys.exit(1)
        
        click.echo(f"\n🔍 블록 #{block_info['block_id']} 상세 정보")
        click.echo("=" * 50)
        click.echo(f"매칭률: {block_info['match_rate']:.1f}%")
        click.echo(f"요약: {block_info.get('summary', '요약 없음')}")
        click.echo(f"필터 조건: {block_info['filter_criteria']}")
        click.echo(f"메시지 수: {block_info['message_count']}개")
        click.echo(f"인덱스 범위: {block_info['start_index']} ~ {block_info['end_index']}")
        click.echo(f"\n첫 번째 메시지:")
        click.echo(f"  📅 {block_info['first_message']['date']}")
        click.echo(f"  👤 {block_info['first_message']['user']}")
        click.echo(f"  💬 {block_info['first_message']['message']}")
        click.echo(f"\n마지막 메시지:")
        click.echo(f"  📅 {block_info['last_message']['date']}")
        click.echo(f"  👤 {block_info['last_message']['user']}")
        click.echo(f"  💬 {block_info['last_message']['message']}")
        click.echo("=" * 50)
        
    except Exception as e:
        click.echo(f"❌ 상세 정보 출력 중 오류 발생: {e}")
        sys.exit(1)


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.argument('filter_criteria', type=str)
@click.option('--window-size', '-w', default=100, help='채팅 윈도우 크기 (기본값: 100)')
@click.option('--overlap', '-o', default=50, help='윈도우 겹침 크기 (기본값: 50)')
@click.option('--model', '-m', default='claude-3-haiku-20240307', help='사용할 Claude 모델')
@click.option('--recent-days', '-d', type=int, help='최근 N일 이내 데이터만 분석')
def estimate(csv_file, filter_criteria, window_size, overlap, model, recent_days):
    """분석 전 예상 비용을 계산합니다."""
    
    try:
        # 분석기 초기화
        from chat_analyzer import ChatAnalyzer
        analyzer = ChatAnalyzer(model=model)
        
        # CSV 로드 및 블록 생성
        chat_data = analyzer.data_manager.load_csv(csv_file, recent_days)
        if not chat_data:
            click.echo("❌ CSV 파일 로드 실패")
            sys.exit(1)
            
        chat_blocks = analyzer.data_manager.create_sliding_windows(window_size, overlap)
        if not chat_blocks:
            click.echo("❌ 채팅 블록 생성 실패")
            sys.exit(1)
        
        # 비용 추정
        estimated_cost = analyzer._estimate_cost_and_time(chat_blocks, filter_criteria)
        
        click.echo(f"\n💰 분석 비용 추정")
        click.echo("=" * 40)
        click.echo(f"모델: {estimated_cost['model']}")
        click.echo(f"총 블록 수: {estimated_cost['total_blocks']:,}개")
        click.echo(f"예상 토큰: {estimated_cost['estimated_tokens']:,}개")
        click.echo(f"  - 입력 토큰: {estimated_cost['total_input_tokens']:,}개")
        click.echo(f"  - 출력 토큰: {estimated_cost['total_output_tokens']:,}개")
        click.echo(f"  - 블록당 평균 입력 토큰: {estimated_cost['avg_input_tokens_per_block']:,}개")
        click.echo(f"예상 시간: {estimated_cost['estimated_time']:.1f}초")
        click.echo(f"예상 비용: ${estimated_cost['total_usd']:.4f}")
        click.echo(f"예상 비용(원): ₩{estimated_cost['total_krw']:.0f}")
        click.echo("=" * 40)
        click.echo("💡 실제 비용은 텍스트 복잡도에 따라 달라질 수 있습니다.")
        
    except Exception as e:
        click.echo(f"❌ 비용 추정 중 오류 발생: {e}")
        sys.exit(1)


@cli.command()
def pricing():
    """모델별 가격 정보를 출력합니다."""
    
    from llm_client import OptimizedClaudeClient
    
    click.echo("💰 Claude 모델별 가격 정보 (1K 토큰당)")
    click.echo("=" * 60)
    
    for model, pricing in OptimizedClaudeClient.MODEL_PRICING.items():
        click.echo(f"\n🤖 {model}")
        click.echo(f"  입력: ${pricing['input']:.5f} (₩{pricing['input'] * 1350:.2f})")
        click.echo(f"  출력: ${pricing['output']:.5f} (₩{pricing['output'] * 1350:.2f})")
    
    click.echo("\n💡 환율: 1 USD = 1,350 KRW (대략)")
    click.echo("💡 추천 모델:")
    click.echo("  - 비용 최적화: claude-3-haiku-20240307")
    click.echo("  - 성능 균형: claude-3-5-sonnet-20240620")


@cli.command()
def setup():
    """환경 설정 가이드를 출력합니다."""
    
    click.echo("🚀 채팅 데이터 분석기 환경 설정 가이드")
    click.echo("=" * 50)
    click.echo("1. 가상환경 설정:")
    click.echo("   ./setup.sh")
    click.echo("")
    click.echo("2. 가상환경 활성화:")
    click.echo("   source activate.sh")
    click.echo("")
    click.echo("3. API 키 설정:")
    click.echo("   .env 파일에 ANTHROPIC_API_KEY=your_key_here 추가")
    click.echo("")
    click.echo("4. CSV 파일 준비:")
    click.echo("   Date,User,Message 형식의 CSV 파일")
    click.echo("")
    click.echo("5. 비용 추정:")
    click.echo("   python main.py estimate chat.csv '긍정적인 대화'")
    click.echo("")
    click.echo("6. 분석 실행:")
    click.echo("   python main.py analyze chat.csv '긍정적인 대화'")
    click.echo("")
    click.echo("7. 결과 검색:")
    click.echo("   python main.py search analysis_results_xxx.json 75")
    click.echo("")
    click.echo("⚡ 성능 최적화 특징 (기본 활성화):")
    click.echo("   - 병렬 처리로 3-5배 빠른 속도")
    click.echo("   - 스마트 캐싱으로 중복 분석 방지")
    click.echo("   - 대용량 파일 자동 샘플링")
    click.echo("   - 실시간 성능 모니터링")
    click.echo("   - 지수 백오프 재시도 로직")
    click.echo("=" * 50)


if __name__ == '__main__':
    cli()