"""
YouTube 트렌드 검색 기능 테스트
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.youtube_service import YouTubeService


class TestPopularityScoreCalculation:
    """트렌드 인기도 점수 계산 테스트"""

    def test_calculate_popularity_score_recent_video(self):
        """2일 전 업로드, 높은 일일 조회수 → 높은 트렌드 점수"""
        # Given: 2일 전 업로드된 비디오
        published_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        video = {
            "snippet": {"publishedAt": published_at.replace("+00:00", "Z")},
            "statistics": {
                "viewCount": "100000",
                "likeCount": "5000",
                "commentCount": "200"
            }
        }
        
        # When: 트렌드 점수 계산
        score, days = YouTubeService._calculate_popularity_score(video)
        
        # Then: 높은 트렌드 점수
        assert days == 2
        assert score > 90000  # 높은 신선도 보너스
        # views_per_day = 50,000
        # recency_weight = 1 + (30-2)/30 = 1.93
        # trend_score = 50,000 * 1.93 = 96,500
        # engagement_score = 5000 * 0.1 + 200 * 0.05 = 510
        # total ≈ 97,010

    def test_calculate_popularity_score_old_video(self):
        """60일 전 업로드, 높은 조회수 → 낮은 트렌드 점수 (신선도 없음)"""
        # Given: 60일 전 업로드된 비디오
        published_at = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        video = {
            "snippet": {"publishedAt": published_at.replace("+00:00", "Z")},
            "statistics": {
                "viewCount": "1000000",
                "likeCount": "50000",
                "commentCount": "2000"
            }
        }
        
        # When: 트렌드 점수 계산
        score, days = YouTubeService._calculate_popularity_score(video)
        
        # Then: 낮은 트렌드 점수 (신선도 보너스 없음)
        assert days == 60
        assert score < 30000  # 신선도 보너스 없음
        # views_per_day = 16,667
        # recency_weight = 1.0 (30일 이후)
        # trend_score = 16,667 * 1.0 = 16,667
        # engagement_score = 50000 * 0.1 + 2000 * 0.05 = 5,100
        # total ≈ 21,767

    def test_calculate_popularity_score_mid_aged_video(self):
        """7일 전 업로드 → 중간 정도의 신선도 보너스"""
        # Given: 7일 전 업로드된 비디오
        published_at = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        video = {
            "snippet": {"publishedAt": published_at.replace("+00:00", "Z")},
            "statistics": {
                "viewCount": "300000",
                "likeCount": "15000",
                "commentCount": "1000"
            }
        }
        
        # When: 트렌드 점수 계산
        score, days = YouTubeService._calculate_popularity_score(video)
        
        # Then: 중간 정도의 트렌드 점수
        assert days == 7
        assert 70000 < score < 80000  # 중간 신선도 보너스
        # views_per_day = 42,857
        # recency_weight = 1 + (30-7)/30 = 1.77
        # trend_score = 42,857 * 1.77 ≈ 75,857
        # engagement_score = 15000 * 0.1 + 1000 * 0.05 = 1,550
        # total ≈ 77,407

    def test_calculate_popularity_score_no_published_date(self):
        """업로드 날짜가 없는 경우 → 0점"""
        # Given: publishedAt이 없는 비디오
        video = {
            "snippet": {},
            "statistics": {
                "viewCount": "100000",
                "likeCount": "5000",
                "commentCount": "200"
            }
        }
        
        # When: 트렌드 점수 계산
        score, days = YouTubeService._calculate_popularity_score(video)
        
        # Then: 0점 반환
        assert score == 0.0
        assert days == 0

    def test_calculate_popularity_score_no_statistics(self):
        """통계 정보가 없는 경우 → 0점"""
        # Given: statistics가 없는 비디오
        published_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        video = {
            "snippet": {"publishedAt": published_at.replace("+00:00", "Z")},
            "statistics": {}
        }
        
        # When: 트렌드 점수 계산
        score, days = YouTubeService._calculate_popularity_score(video)
        
        # Then: 0점 반환 (통계 없음)
        assert score == 0.0
        assert days == 2


class TestQueryBuilder:
    """검색 쿼리 생성 테스트"""

    def test_build_query_keywords_only(self):
        """keywords만 있는 경우"""
        # Given: keywords만 제공
        keywords = "python tutorial"
        title = None
        
        # When: 쿼리 생성
        query = YouTubeService._build_query(keywords, title)
        
        # Then: keywords만 반환
        assert query == "python tutorial"

    def test_build_query_with_single_word_title(self):
        """title이 단일 단어인 경우"""
        # Given: keywords + 단일 단어 title
        keywords = "python tutorial"
        title = "beginner"
        
        # When: 쿼리 생성
        query = YouTubeService._build_query(keywords, title)
        
        # Then: intitle: 연산자 사용
        assert query == "python tutorial intitle:beginner"

    def test_build_query_with_multi_word_title(self):
        """title이 여러 단어인 경우"""
        # Given: keywords + 여러 단어 title
        keywords = "python"
        title = "for beginners"
        
        # When: 쿼리 생성
        query = YouTubeService._build_query(keywords, title)
        
        # Then: intitle: 연산자 + 따옴표
        assert query == 'python intitle:"for beginners"'

    def test_build_query_korean(self):
        """한국어 검색어"""
        # Given: 한국어 keywords + title
        keywords = "파이썬 강의"
        title = "초보자"
        
        # When: 쿼리 생성
        query = YouTubeService._build_query(keywords, title)
        
        # Then: intitle: 연산자 사용
        assert query == "파이썬 강의 intitle:초보자"


class TestVideoSorting:
    """비디오 정렬 테스트"""

    def test_videos_sorted_by_popularity_score(self):
        """비디오가 popularity_score 기준으로 정렬되는지 검증"""
        # Given: 다양한 점수를 가진 비디오 리스트
        videos = [
            {"id": "video1", "popularity_score": 50000, "days_since_upload": 10},
            {"id": "video2", "popularity_score": 90000, "days_since_upload": 2},
            {"id": "video3", "popularity_score": 70000, "days_since_upload": 7},
        ]
        
        # When: 정렬
        sorted_videos = sorted(
            videos,
            key=lambda x: x.get("popularity_score", 0),
            reverse=True
        )
        
        # Then: 내림차순 정렬
        assert sorted_videos[0]["id"] == "video2"  # 90000
        assert sorted_videos[1]["id"] == "video3"  # 70000
        assert sorted_videos[2]["id"] == "video1"  # 50000


# pytest 실행 방법:
# cd BE
# pytest tests/services/test_youtube_search.py -v
