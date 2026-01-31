"""
기존 CompetitorVideo 데이터에 대해 자막 재다운로드 스크립트

사용법:
    python scripts/reprocess_subtitles.py [--limit N]
    
주의사항:
    - YouTube Rate Limiting으로 인해 429 에러가 발생할 수 있습니다
    - Rate Limiting: 비디오당 5초 대기
    - 대량 처리 시 여러 번 나눠서 실행하세요
"""
import asyncio
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.db import async_session
from app.models.competitor import CompetitorVideo
from app.services.subtitle_service import SubtitleService


async def reprocess_all_subtitles(limit: int = None):
    """
    모든 CompetitorVideo에 대해 자막 재다운로드.
    
    Args:
        limit: 처리할 최대 비디오 수 (None이면 전체)
    """
    print("=" * 70)
    print("YouTube 자막 재처리 시작")
    print("=" * 70)
    
    async with async_session() as db:
        # CompetitorVideo 조회
        stmt = select(CompetitorVideo)
        if limit:
            stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        videos = result.scalars().all()
        
        total = len(videos)
        print(f"\n처리 대상: {total}개 비디오")
        print(f"예상 소요 시간: 약 {total * 5 / 60:.1f}분 (비디오당 5초)\n")
        
        success_count = 0
        failed_count = 0
        no_caption_count = 0
        
        for i, video in enumerate(videos, 1):
            print(f"[{i}/{total}] {video.youtube_video_id}: {video.title[:50]}...")
            
            try:
                # 자막 다운로드
                results = await SubtitleService.fetch_subtitles(
                    video_ids=[video.youtube_video_id],
                    languages=['ko', 'en'],
                    db=db
                )
                
                if results:
                    result = results[0]
                    if result['status'] == 'success':
                        success_count += 1
                        tracks = result.get('tracks', [])
                        if tracks:
                            track = tracks[0]
                            print(f"  ✓ 성공: {track['language_code']} "
                                  f"({'자동' if track['is_auto_generated'] else '수동'}) "
                                  f"- {len(track['cues'])}개 세그먼트")
                    elif result.get('no_captions'):
                        no_caption_count += 1
                        print(f"  - 자막 없음")
                    else:
                        failed_count += 1
                        print(f"  ✗ 실패: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                failed_count += 1
                print(f"  ✗ 예외 발생: {e}")
                
                # 429 에러 시 중단
                if "429" in str(e) or "Too Many Requests" in str(e):
                    print(f"\n⚠️  YouTube Rate Limiting 감지!")
                    print(f"현재까지 처리: {i}/{total}")
                    print(f"성공: {success_count}, 자막없음: {no_caption_count}, 실패: {failed_count}")
                    print(f"\n해결 방법:")
                    print(f"1. 30분~1시간 대기 후 재실행")
                    print(f"2. --limit 옵션으로 소량씩 처리")
                    print(f"3. Proxy 서비스 사용 (Webshare 등)")
                    return
            
            # 진행률 표시
            if i % 10 == 0:
                print(f"\n진행률: {i}/{total} ({i/total*100:.1f}%)")
                print(f"성공: {success_count}, 자막없음: {no_caption_count}, 실패: {failed_count}\n")
    
    print("\n" + "=" * 70)
    print("재처리 완료!")
    print("=" * 70)
    print(f"총 처리: {total}개")
    print(f"성공: {success_count}개")
    print(f"자막 없음: {no_caption_count}개")
    print(f"실패: {failed_count}개")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube 자막 재처리")
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='처리할 최대 비디오 수 (기본: 전체)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(reprocess_all_subtitles(limit=args.limit))
