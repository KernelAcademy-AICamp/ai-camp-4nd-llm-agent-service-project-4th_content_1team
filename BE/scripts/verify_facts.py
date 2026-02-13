"""
최근 생성된 스크립트의 팩트 인용 패턴 분석.
- 전달된 팩트 수 vs 실제 인용된 팩트 수 비교
- 챕터별 인용 분포 확인
"""
import asyncio
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 최근 스크립트 결과 가져오기
        result = await session.execute(text("""
            SELECT sd.id, sd.topic_request_id, sd.result_json 
            FROM script_drafts sd 
            ORDER BY sd.created_at DESC 
            LIMIT 1
        """))
        row = result.fetchone()

        if not row:
            print("No script drafts found")
            return

        topic_request_id = row[1]
        draft_json = row[2]

        print(f"=== Topic Request ID: {topic_request_id} ===")

        # 2. 해당 topic의 fact_set (전달된 팩트들) 가져오기
        fact_result = await session.execute(text("""
            SELECT facts_json FROM fact_sets 
            WHERE topic_request_id = :tid
            ORDER BY created_at DESC LIMIT 1
        """), {"tid": str(topic_request_id)})
        fact_row = fact_result.fetchone()

        facts = []
        if fact_row:
            facts_data = fact_row[0]
            if isinstance(facts_data, str):
                facts_data = json.loads(facts_data)
            facts = facts_data if isinstance(facts_data, list) else facts_data.get("structured_facts", [])
            print(f"\n📦 전달된 팩트 수: {len(facts)}개")

            # 기사별 팩트 분포
            source_counts = {}
            for f in facts:
                src = f.get("source_name", "Unknown")
                source_counts[src] = source_counts.get(src, 0) + 1
            print("\n📰 기사별 팩트 분포:")
            for src, cnt in source_counts.items():
                print(f"   - {src}: {cnt}개")

        # 3. 스크립트에서 인용 패턴 분석
        if draft_json:
            if isinstance(draft_json, str):
                draft_json = json.loads(draft_json)

            script = draft_json.get("script", {})

            # Hook
            hook_text = script.get("hook", {}).get("text", "")
            hook_refs = script.get("hook", {}).get("fact_references", [])
            hook_circles = re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]", hook_text)
            print("\n📝 Hook:")
            print(f"   - 텍스트 길이: {len(hook_text)}자")
            print(f"   - fact_references: {len(hook_refs)}개")
            print(f"   - 인라인 인용(①②③): {len(hook_circles)}개 → {hook_circles}")

            # Chapters
            chapters = script.get("chapters", [])
            all_chapter_text = ""
            all_chapter_refs = []
            for ch in chapters:
                title = ch.get("title", "")
                beats = ch.get("beats", [])
                ch_text = ""
                ch_refs = []
                for beat in beats:
                    ch_text += beat.get("line", "") + " "
                    ch_refs.extend(beat.get("fact_references", []))
                all_chapter_text += ch_text
                all_chapter_refs.extend(ch_refs)

                circles = re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]", ch_text)
                print(f"\n📝 Chapter: {title}")
                print(f"   - 텍스트 길이: {len(ch_text)}자")
                print(f"   - fact_references: {len(ch_refs)}개")
                print(f"   - 인라인 인용(①②③): {len(circles)}개 → {circles}")

            # Outro
            outro_text = script.get("closing", {}).get("text", "")

            # 전체 인용 분석
            full_text = hook_text + " " + all_chapter_text + " " + outro_text
            all_circles = re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]", full_text)
            unique_circles = sorted(set(all_circles))

            all_refs = hook_refs + all_chapter_refs
            unique_refs = set(all_refs)

            print(f"\n{'='*50}")
            print(f"📊 종합 검증 결과")
            print(f"{'='*50}")
            print(f"전달된 팩트 총 수:     {len(facts)}개")
            print(f"사용된 출처 번호:      {unique_circles} ({len(unique_circles)}개)")
            print(f"총 인라인 인용 횟수:   {len(all_circles)}회")
            print(f"fact_references 총 수: {len(all_refs)}개 (고유: {len(unique_refs)}개)")
            print(f"스크립트 전체 길이:    {len(full_text)}자")

            # 인용 밀도 계산
            density = len(all_circles) / (len(full_text) / 1000) if full_text else 0
            print(f"인용 밀도:             {density:.1f}회/1000자")

            if len(facts) > 0:
                coverage = len(unique_refs) / len(facts) * 100
                print(f"팩트 사용률:           {coverage:.0f}% ({len(unique_refs)}/{len(facts)})")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
