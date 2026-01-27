## 2026-01-26T00:00:00Z 요청 기록

YOUTUBE_CHANNELS {
    text id PK "youtube_channel_id"
    uuid user_id FK
    text title "NULL"
    text description "NULL"
    text country "NULL"
    text keywords "NULL"
    jsonb raw_channel_json
    timestamptz created_at
    timestamptz updated_at
  }

  YT_CHANNEL_STATS_DAILY {
    uuid id PK
    text channel_id FK
    date date
    int subscriber_count "NULL"
    bigint view_count "NULL"
    int video_count "NULL"
    int comment_count "NULL"
    jsonb raw_stats_json "NULL"
    timestamptz created_at
  }

  YT_CHANNEL_TOPICS {
    uuid id PK
    text channel_id FK
    text topic_category_url
    timestamptz created_at
  }

  YT_AUDIENCE_DAILY {
    uuid id PK
    text channel_id FK
    date date
    text age_group
    text gender
    float viewer_percentage "NULL"
    int views "NULL"
    float watch_time_minutes "NULL"
    jsonb raw_report_json "NULL"
    timestamptz created_at
  }

  YT_GEO_DAILY {
    uuid id PK
    text channel_id FK
    date date
    text country
    float viewer_percentage "NULL"
    int views "NULL"
    float watch_time_minutes "NULL"
    jsonb raw_report_json "NULL"
    timestamptz created_at
  }

이데이터 베이스 디자인을 참고해서 데이터베이스를 생성하고 유투브 api를 이용해서 구글로그인시 사용자 채널 정보를 가져와서 데이터베이스에 저장할 수 있게 해줘
