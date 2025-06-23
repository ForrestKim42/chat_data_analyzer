"""
CSV 파일 읽기 및 데이터 처리 모듈
Date,User,Message 형식의 CSV 파일을 처리
"""

import pandas as pd
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class DataManager:
    """CSV 데이터 읽기/쓰기 및 처리를 담당하는 클래스"""
    
    def __init__(self):
        self.chat_data = []
    
    def load_csv(self, file_path: str, recent_days: Optional[int] = None) -> List[Dict[str, str]]:
        """
        CSV 파일을 읽어서 채팅 데이터로 변환
        
        Args:
            file_path: CSV 파일 경로
            recent_days: 최근 N일 이내 데이터만 로드 (None이면 전체)
        
        Returns:
            채팅 데이터 리스트 [{"date": "...", "user": "...", "message": "..."}]
        """
        try:
            # CSV 파일 읽기
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 컬럼명 확인 및 표준화
            expected_columns = ['Date', 'User', 'Message']
            if not all(col in df.columns for col in expected_columns):
                raise ValueError(f"CSV 파일에 필요한 컬럼이 없습니다. 필요한 컬럼: {expected_columns}")
            
            # 데이터 정리
            df = df.dropna(subset=['Message'])  # 메시지가 없는 행 제거
            df['Message'] = df['Message'].astype(str).str.strip()  # 메시지 공백 제거
            df = df[df['Message'] != '']  # 빈 메시지 제거
            
            # 날짜 필터링 (recent_days가 지정된 경우)
            if recent_days is not None:
                df = self._filter_by_recent_days(df, recent_days)
            
            # 딕셔너리 리스트로 변환
            chat_data = []
            for _, row in df.iterrows():
                chat_data.append({
                    'date': str(row['Date']).strip(),
                    'user': str(row['User']).strip(),
                    'message': str(row['Message']).strip()
                })
            
            self.chat_data = chat_data
            filter_msg = f" (최근 {recent_days}일)" if recent_days else ""
            print(f"✅ CSV 파일 로드 완료{filter_msg}: {len(chat_data)}개의 메시지")
            return chat_data
            
        except Exception as e:
            print(f"❌ CSV 파일 로드 중 오류 발생: {e}")
            return []
    
    def create_sliding_windows(self, window_size: int = 100, overlap: int = 50) -> List[List[Dict[str, str]]]:
        """
        슬라이딩 윈도우 방식으로 채팅 데이터를 분할
        
        Args:
            window_size: 윈도우 크기 (기본값: 100)
            overlap: 겹치는 메시지 수 (기본값: 50)
        
        Returns:
            채팅 블록들의 리스트
        """
        if not self.chat_data:
            print("❌ 로드된 채팅 데이터가 없습니다.")
            return []
        
        blocks = []
        step = window_size - overlap
        
        for i in range(0, len(self.chat_data), step):
            block = self.chat_data[i:i + window_size]
            if len(block) >= 10:  # 최소 10개 메시지가 있는 블록만 포함
                blocks.append(block)
            
            # 마지막 블록이 윈도우 크기보다 작으면 중단
            if i + window_size >= len(self.chat_data):
                break
        
        print(f"✅ 슬라이딩 윈도우 생성 완료: {len(blocks)}개의 블록")
        return blocks
    
    def save_analysis_results(self, results: List[Dict[str, Any]], file_path: str = None) -> str:
        """
        분석 결과를 JSON 파일로 저장
        
        Args:
            results: 분석 결과 리스트
            file_path: 저장할 파일 경로 (None이면 자동 생성)
        
        Returns:
            저장된 파일 경로
        """
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"analysis_results_{timestamp}.json"
        
        try:
            # 결과 데이터 구조화
            output_data = {
                "analysis_info": {
                    "timestamp": datetime.now().isoformat(),
                    "total_blocks": len(results),
                    "total_messages": len(self.chat_data)
                },
                "results": results
            }
            
            # JSON 파일로 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 분석 결과 저장 완료: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"❌ 결과 저장 중 오류 발생: {e}")
            return ""
    
    def load_analysis_results(self, file_path: str) -> List[Dict[str, Any]]:
        """
        저장된 분석 결과를 로드
        
        Args:
            file_path: 결과 파일 경로
        
        Returns:
            분석 결과 리스트
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            print(f"✅ 분석 결과 로드 완료: {len(results)}개의 블록")
            return results
            
        except Exception as e:
            print(f"❌ 결과 로드 중 오류 발생: {e}")
            return []
    
    def filter_by_threshold(self, results: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """
        임계값 이상의 매칭률을 가진 블록들을 필터링
        
        Args:
            results: 분석 결과 리스트
            threshold: 임계값 (0-100)
        
        Returns:
            필터링된 결과 리스트
        """
        filtered_results = [
            result for result in results 
            if result.get('match_rate', 0) >= threshold
        ]
        
        print(f"✅ 임계값 {threshold}% 이상 블록: {len(filtered_results)}개")
        return filtered_results
    
    def get_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        분석 결과 통계 계산
        
        Args:
            results: 분석 결과 리스트
        
        Returns:
            통계 정보 딕셔너리
        """
        if not results:
            return {}
        
        match_rates = [result.get('match_rate', 0) for result in results]
        
        stats = {
            "total_blocks": len(results),
            "average_match_rate": sum(match_rates) / len(match_rates),
            "max_match_rate": max(match_rates),
            "min_match_rate": min(match_rates),
            "blocks_above_50": len([r for r in match_rates if r >= 50]),
            "blocks_above_75": len([r for r in match_rates if r >= 75])
        }
        
        return stats
    
    def _filter_by_recent_days(self, df: pd.DataFrame, recent_days: int) -> pd.DataFrame:
        """
        최근 N일 이내의 데이터만 필터링
        
        Args:
            df: 원본 DataFrame
            recent_days: 최근 N일
        
        Returns:
            필터링된 DataFrame
        """
        try:
            # 현재 날짜에서 N일 전 계산
            cutoff_date = datetime.now() - timedelta(days=recent_days)
            
            # Date 컬럼을 datetime으로 변환 (다양한 형식 시도)
            date_formats = [
                '%Y-%m-%d %H:%M:%S',  # 2024-06-23 14:30:22
                '%Y-%m-%d',           # 2024-06-23
                '%Y/%m/%d %H:%M:%S',  # 2024/06/23 14:30:22
                '%Y/%m/%d',           # 2024/06/23
                '%m/%d/%Y %H:%M:%S',  # 06/23/2024 14:30:22
                '%m/%d/%Y',           # 06/23/2024
                '%d/%m/%Y %H:%M:%S',  # 23/06/2024 14:30:22
                '%d/%m/%Y'            # 23/06/2024
            ]
            
            df_filtered = df.copy()
            parsed_dates = None
            
            for date_format in date_formats:
                try:
                    parsed_dates = pd.to_datetime(df_filtered['Date'], format=date_format, errors='coerce')
                    if not parsed_dates.isna().all():  # 일부라도 파싱되면 성공
                        break
                except:
                    continue
            
            # 파싱이 실패한 경우 기본 파싱 시도
            if parsed_dates is None or parsed_dates.isna().all():
                parsed_dates = pd.to_datetime(df_filtered['Date'], errors='coerce')
            
            # 파싱 실패한 행들 제거
            valid_dates_mask = ~parsed_dates.isna()
            if not valid_dates_mask.any():
                print(f"⚠️ 날짜 파싱 실패 - 전체 데이터를 사용합니다")
                return df
            
            df_filtered = df_filtered[valid_dates_mask]
            parsed_dates = parsed_dates[valid_dates_mask]
            
            # 최근 N일 이내 데이터 필터링
            recent_mask = parsed_dates >= cutoff_date
            df_recent = df_filtered[recent_mask]
            
            original_count = len(df)
            filtered_count = len(df_recent)
            
            print(f"📅 날짜 필터링: {original_count}개 → {filtered_count}개 메시지 (최근 {recent_days}일)")
            
            if filtered_count == 0:
                print(f"⚠️ 최근 {recent_days}일 이내 데이터가 없습니다. 전체 데이터를 사용합니다.")
                return df
            
            return df_recent
            
        except Exception as e:
            print(f"⚠️ 날짜 필터링 중 오류 발생: {e}")
            print("전체 데이터를 사용합니다.")
            return df