from app.services.youtube_service import YouTubeService


def test_parse_channel_item_converts_types_and_merges_keywords():
    item = {
        "id": "channel123",
        "snippet": {
            "title": "My Channel",
            "description": "Desc",
            "country": "KR",
        },
        "statistics": {
            "subscriberCount": "100",
            "viewCount": "2000",
            "videoCount": "3",
            "commentCount": "7",
        },
        "topicDetails": {
            "topicCategories": [
                "https://en.wikipedia.org/wiki/Topic_A",
                "https://en.wikipedia.org/wiki/Topic_B",
            ]
        },
        "brandingSettings": {
            "channel": {
                "keywords": ["foo", "bar"],
            }
        },
    }

    parsed = YouTubeService.parse_channel_item(item)

    assert parsed["channel_id"] == "channel123"
    assert parsed["title"] == "My Channel"
    assert parsed["description"] == "Desc"
    assert parsed["country"] == "KR"
    assert parsed["keywords"] == "foo,bar"

    stats = parsed["stats"]
    assert stats["subscriber_count"] == 100
    assert stats["view_count"] == 2000
    assert stats["video_count"] == 3
    assert stats["comment_count"] == 7
    assert stats["raw_stats_json"]["subscriberCount"] == "100"

    topics = parsed["topics"]
    assert set(topics) == {
        "https://en.wikipedia.org/wiki/Topic_A",
        "https://en.wikipedia.org/wiki/Topic_B",
    }
