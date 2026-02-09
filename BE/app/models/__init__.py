from app.models.user import User
from app.models.oauth import OAuthAccount
from app.models.session import Session
from app.models.jwt_token import JWTRefreshToken
from app.models.youtube_channel import (
    YouTubeChannel,
    YTChannelStatsDaily,
    YTChannelTopic,
    YTAudienceDaily,
    YTGeoDaily,
)
from app.models.thumbnail_strategy import ThumbnailStrategy
from app.models.thumbnail_generation import ThumbnailGeneration
from app.models.competitor import CompetitorCollection, CompetitorVideo, VideoCommentSample
from app.models.caption import VideoCaption
from app.models.video_content_analysis import VideoContentAnalysis
from app.models.content_topic import ChannelTopic, TrendTopic
from app.models.competitor_channel import CompetitorChannel
from app.models.competitor_channel_video import CompetitorRecentVideo, RecentVideoComment, RecentVideoCaption

# 스크립트 생성 파이프라인 모델
from app.models.topic_request import TopicRequest, AgentRun
from app.models.script_pipeline import (
    ContentBrief,
    ArticleSet, Article, ArticleAsset,
    FactSet, Fact, FactEvidence, FactDedupeCluster,
    VisualPlan, InsightSentence,
    InsightPack,
)
from app.models.script_output import (
    ScriptDraft, ScriptClaim, ScriptSourceMap,
    VerifiedScript,
)

__all__ = [
    "User",
    "OAuthAccount",
    "Session",
    "JWTRefreshToken",
    "YouTubeChannel",
    "YTChannelStatsDaily",
    "YTChannelTopic",
    "YTAudienceDaily",
    "YTGeoDaily",
    "ThumbnailStrategy",
    "ThumbnailGeneration",
    "CompetitorCollection",
    "CompetitorVideo",
    "VideoCommentSample",
    "VideoCaption",
    "VideoContentAnalysis",
    "ChannelTopic",
    "TrendTopic",
    "CompetitorChannel",
    "CompetitorRecentVideo",
    "RecentVideoComment",
    "RecentVideoCaption",
    # 파이프라인 공통
    "TopicRequest",
    "AgentRun",
    # Planner + News Research + Insight Builder
    "ContentBrief",
    "ArticleSet",
    "Article",
    "ArticleAsset",
    "FactSet",
    "Fact",
    "FactEvidence",
    "FactDedupeCluster",
    "VisualPlan",
    "InsightSentence",
    "InsightPack",
    # Writer + Verifier
    "ScriptDraft",
    "ScriptClaim",
    "ScriptSourceMap",
    "VerifiedScript",
]

