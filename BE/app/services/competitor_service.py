from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import CompetitorCollection, CompetitorVideo
from app.schemas.competitor import CompetitorSaveRequest


class CompetitorService:

    @staticmethod
    async def save_collection(
        db: AsyncSession, req: CompetitorSaveRequest
    ) -> CompetitorCollection:
        collection = CompetitorCollection(policy_json=req.policy_json)

        for v in req.videos:
            collection.videos.append(
                CompetitorVideo(
                    youtube_video_id=v.youtube_video_id,
                    url=v.url,
                    title=v.title,
                    channel_title=v.channel_title,
                    published_at=v.published_at,
                    duration_sec=v.duration_sec,
                    metrics_json=v.metrics_json,
                    caption_meta_json=v.caption_meta_json,
                    selection_json=v.selection_json,
                )
            )

        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        return collection
