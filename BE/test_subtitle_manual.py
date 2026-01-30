"""
YouTube 자막 다운로드 테스트 스크립트
"""
import asyncio
from app.services.subtitle_service import SubtitleService

# 테스트 비디오 목록
test_videos = [
    {
        "name": "영어 수동 자막 (Rick Astley)",
        "video_id": "dQw4w9WgXcQ",
        "expected": "en 수동 자막"
    },
    {
        "name": "인기 영어 강의 (Python Tutorial)",
        "video_id": "rfscVS0vtbw",
        "expected": "en 자동/수동 자막"
    },
    {
        "name": "한국어 콘텐츠",
        "video_id": "_uQrJ0TkZlc",  # 인기 한국 YouTube 비디오
        "expected": "ko 자막"
    }
]

async def test_subtitles():
    print("=" * 60)
    print("YouTube 자막 다운로드 테스트")
    print("=" * 60)
    
    for test in test_videos:
        print(f"\n테스트: {test['name']}")
        print(f"Video ID: {test['video_id']}")
        print(f"예상: {test['expected']}")
        print("-" * 60)
        
        try:
            result = await SubtitleService._fetch_with_library(
                test['video_id'],
                languages=['ko', 'en']
            )
            
            print(f"상태: {result['status']}")
            print(f"소스: {result['source']}")
            print(f"자막 없음: {result['no_captions']}")
            print(f"트랙 수: {len(result['tracks'])}")
            
            if result['tracks']:
                for track in result['tracks']:
                    print(f"  - 언어: {track['language_code']} ({track['language_name']})")
                    print(f"    자동 생성: {track['is_auto_generated']}")
                    print(f"    세그먼트 수: {len(track['cues'])}")
                    if track['cues']:
                        # 첫 3개 세그먼트 출력
                        print(f"    첫 세그먼트:")
                        for i, cue in enumerate(track['cues'][:3]):
                            print(f"      [{cue['start']:.1f}s] {cue['text'][:50]}...")
            
            if result['error']:
                print(f"에러: {result['error']}")
                
        except Exception as e:
            print(f"테스트 실패: {e}")
        
        print()
    
    print("=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_subtitles())
