"""has_caption=true인 비디오 ID 확인 및 자막 테스트"""
import asyncio
from sqlalchemy import select, text
from app.core.db import AsyncSessionLocal
from app.models.competitor import CompetitorVideo
from app.services.subtitle_service import SubtitleService
from app.core.config import settings

async def test_has_caption_videos():
    async with AsyncSessionLocal() as db:
        # has_caption=true인 비디오 3개 조회
        stmt = text("""
            SELECT youtube_video_id, title, caption_meta_json 
            FROM competitor_videos 
            WHERE caption_meta_json->>'has_caption' = 'true' 
            LIMIT 5
        """)
        
        result = await db.execute(stmt)
        rows = result.fetchall()
        
        print("=" * 70)
        print("has_caption=true인 비디오 테스트")
        print("=" * 70)
        
        for i, row in enumerate(rows, 1):
            video_id = row[0]
            title = row[1]
            caption_meta = row[2]
            
            print(f"\n[{i}] Video ID: {video_id}")
            print(f"    제목: {title[:70]}")
            print(f"    Caption Meta: {caption_meta}")
            print("-" * 70)
            
            # 실제 자막 다운로드 시도 (Cookies + Proxy 사용)
            try:
                proxies = SubtitleService._get_proxy_config()
                print(f"    설정: Cookies={settings.youtube_cookies_file}, Proxy={bool(proxies)}")
                
                result = await SubtitleService._fetch_with_library(
                    video_id,
                    languages=['ko', 'en'],
                    cookies=settings.youtube_cookies_file,
                    proxies=proxies
                )
                
                print(f"    결과: {result['status']}")
                print(f"    소스: {result['source']}")
                print(f"    자막 없음: {result['no_captions']}")
                
                if result['tracks']:
                    for track in result['tracks']:
                        print(f"    ✓ 자막 발견: {track['language_code']} "
                              f"({'자동' if track['is_auto_generated'] else '수동'}) "
                              f"- {len(track['cues'])}개 세그먼트")
                        # 첫 2개 세그먼트 출력
                        for cue in track['cues'][:2]:
                            print(f"      [{cue['start']:.1f}s] {cue['text'][:50]}")
                else:
                    print(f"    ✗ 자막 없음")
                
                if result['error']:
                    print(f"    에러: {result['error'][:100]}")
                    
            except Exception as e:
                print(f"    ✗ 예외 발생: {e}")
                
                # 429 에러 확인
                if "429" in str(e):
                    print(f"\n⚠️  YouTube Rate Limiting 발생!")
                    print(f"10분 후 다시 시도하거나 Proxy를 사용하세요.")
                    break
            
            # 다음 비디오 전 대기 (Rate Limiting)
            if i < len(rows):
                await asyncio.sleep(5)
        
        print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(test_has_caption_videos())
