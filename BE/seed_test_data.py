"""
테스트용 더미 데이터 시딩 스크립트

실행 방법:
    cd BE
    python seed_test_data.py

생성되는 데이터:
    - yt_audience_daily: 시청자 인구통계 (나이/성별)
    - yt_geo_daily: 지역별 통계
    - yt_channel_stats_daily: 채널 일별 통계
"""
import asyncio
from datetime import date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# 코딩알려주는누나 채널 ID
TEST_CHANNEL_ID = "UCfBvs0ZJdTA43NQrnI9imGA"  # 코딩알려주는누나


async def seed_test_data():
    """테스트용 더미 데이터 삽입."""

    # DB 연결
    engine = create_async_engine(settings.database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        today = date.today()
        now = datetime.utcnow()

        # 기존 테스트 데이터 삭제
        await db.execute(text(f"DELETE FROM yt_audience_daily WHERE channel_id = '{TEST_CHANNEL_ID}'"))
        await db.execute(text(f"DELETE FROM yt_geo_daily WHERE channel_id = '{TEST_CHANNEL_ID}'"))
        await db.execute(text(f"DELETE FROM yt_channel_stats_daily WHERE channel_id = '{TEST_CHANNEL_ID}'"))
        await db.commit()

        print("기존 테스트 데이터 삭제 완료")

        # =================================================================
        # 0. 테스트 유저 + 채널 생성 (FK 제약 조건 충족)
        # =================================================================
        TEST_USER_EMAIL = "test@test.com"

        # 테스트 유저 확인/생성
        result = await db.execute(text(f"SELECT id FROM users WHERE email = '{TEST_USER_EMAIL}'"))
        user_row = result.fetchone()

        if user_row:
            test_user_id = user_row[0]
            print(f"기존 테스트 유저 발견: {test_user_id}")
        else:
            test_user_id = str(uuid4())
            await db.execute(text("""
                INSERT INTO users (id, email, name, google_sub, created_at, updated_at)
                VALUES (:id, :email, :name, :google_sub, :created_at, :updated_at)
            """), {
                "id": test_user_id,
                "email": TEST_USER_EMAIL,
                "name": "테스트 유저",
                "google_sub": "test_google_sub",
                "created_at": now,
                "updated_at": now,
            })
            print(f"테스트 유저 생성: {test_user_id}")

        # 테스트 채널 확인/생성
        result = await db.execute(text(f"SELECT channel_id FROM youtube_channels WHERE channel_id = '{TEST_CHANNEL_ID}'"))
        channel_row = result.fetchone()

        if not channel_row:
            await db.execute(text("""
                INSERT INTO youtube_channels (channel_id, user_id, title, description, raw_channel_json, created_at, updated_at)
                VALUES (:channel_id, :user_id, :title, :description, :raw_channel_json, :created_at, :updated_at)
            """), {
                "channel_id": TEST_CHANNEL_ID,
                "user_id": test_user_id,
                "title": "코딩알려주는누나",
                "description": "코딩 교육 채널",
                "raw_channel_json": '{"test": true}',
                "created_at": now,
                "updated_at": now,
            })
            print(f"테스트 채널 생성: {TEST_CHANNEL_ID}")
        else:
            print(f"기존 테스트 채널 발견: {TEST_CHANNEL_ID}")

        await db.commit()

        # =================================================================
        # 1. yt_audience_daily (시청자 인구통계)
        # =================================================================
        audience_data = [
            # 남성
            {"age_group": "13-17", "gender": "male", "viewer_percentage": 5.0},
            {"age_group": "18-24", "gender": "male", "viewer_percentage": 25.0},
            {"age_group": "25-34", "gender": "male", "viewer_percentage": 35.0},
            {"age_group": "35-44", "gender": "male", "viewer_percentage": 10.0},
            {"age_group": "45-54", "gender": "male", "viewer_percentage": 3.0},
            # 여성
            {"age_group": "13-17", "gender": "female", "viewer_percentage": 2.0},
            {"age_group": "18-24", "gender": "female", "viewer_percentage": 10.0},
            {"age_group": "25-34", "gender": "female", "viewer_percentage": 8.0},
            {"age_group": "35-44", "gender": "female", "viewer_percentage": 2.0},
        ]

        for data in audience_data:
            await db.execute(text("""
                INSERT INTO yt_audience_daily
                (id, channel_id, date, age_group, gender, viewer_percentage, created_at)
                VALUES (:id, :channel_id, :date, :age_group, :gender, :viewer_percentage, :created_at)
            """), {
                "id": str(uuid4()),
                "channel_id": TEST_CHANNEL_ID,
                "date": today,
                "age_group": data["age_group"],
                "gender": data["gender"],
                "viewer_percentage": data["viewer_percentage"],
                "created_at": now,
            })

        print(f"yt_audience_daily: {len(audience_data)}개 삽입 완료")

        # =================================================================
        # 2. yt_geo_daily (지역별 통계)
        # =================================================================
        geo_data = [
            {"country": "KR", "viewer_percentage": 82.0},
            {"country": "US", "viewer_percentage": 8.0},
            {"country": "JP", "viewer_percentage": 3.0},
            {"country": "VN", "viewer_percentage": 2.0},
            {"country": "TW", "viewer_percentage": 1.5},
            {"country": "CA", "viewer_percentage": 1.0},
            {"country": "AU", "viewer_percentage": 0.8},
            {"country": "GB", "viewer_percentage": 0.7},
        ]

        for data in geo_data:
            await db.execute(text("""
                INSERT INTO yt_geo_daily
                (id, channel_id, date, country, viewer_percentage, created_at)
                VALUES (:id, :channel_id, :date, :country, :viewer_percentage, :created_at)
            """), {
                "id": str(uuid4()),
                "channel_id": TEST_CHANNEL_ID,
                "date": today,
                "country": data["country"],
                "viewer_percentage": data["viewer_percentage"],
                "created_at": now,
            })

        print(f"yt_geo_daily: {len(geo_data)}개 삽입 완료")

        # =================================================================
        # 3. yt_channel_stats_daily (채널 일별 통계)
        # =================================================================
        # 최근 30일치 데이터 생성
        base_subscribers = 450000
        base_views = 50000000
        base_videos = 200

        for i in range(30):
            stat_date = today - timedelta(days=i)
            # 약간의 변동 추가
            subscribers = base_subscribers + (i * 100)  # 매일 100명씩 증가 가정
            views = base_views + (i * 50000)

            await db.execute(text("""
                INSERT INTO yt_channel_stats_daily
                (id, channel_id, date, subscriber_count, view_count, video_count, created_at)
                VALUES (:id, :channel_id, :date, :subscriber_count, :view_count, :video_count, :created_at)
            """), {
                "id": str(uuid4()),
                "channel_id": TEST_CHANNEL_ID,
                "date": stat_date,
                "subscriber_count": subscribers,
                "view_count": views,
                "video_count": base_videos,
                "created_at": now,
            })

        print(f"yt_channel_stats_daily: 30개 삽입 완료")

        await db.commit()
        print("\n✅ 테스트 더미 데이터 시딩 완료!")


if __name__ == "__main__":
    asyncio.run(seed_test_data())
