from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

# Redis 브로커 주소 설정 (기본값: 로컬)
# Docker Compose 사용 시 'redis' 호스트명 사용
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker"] # 작업을 정의할 워커 모듈 포함
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=False,
    # 작업 결과 만료 시간 (1시간)
    result_expires=3600,
    # Celery Beat 스케줄
    beat_schedule={
        # 매일 오전 6시에 경쟁 유튜버 최신 영상 업데이트
        "update-competitor-videos-daily": {
            "task": "app.worker.task_update_all_competitor_videos",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
