"""
Visual Director Agent

비주얼 전략 생성 에이전트 (GPT-4o 기반)
- 선택된 제목 + 전략 → Visual Strategy JSON 생성
- Nano Banana Best Practices 반영
- 이미지 레퍼런스 정보 포함
"""

import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class VisualDirectorAgent:
    """
    Visual Director Agent
    
    선택된 제목과 전략을 바탕으로 구조화된 Visual Strategy를 생성합니다.
    """
    
    # 시스템 프롬프트
    SYSTEM_PROMPT = """# Role
당신은 유튜브 썸네일 비주얼 전략가입니다.
제목과 키워드를 시각적 요소로 변환하여 구조화된 비주얼 전략을 수립하는 것이 당신의 임무입니다.

# Task
주어진 제목, 키워드, 이미지 레퍼런스를 바탕으로 **Visual Strategy**를 생성하세요.

# Output Structure

## 1. Purpose (목적)
- 이 썸네일이 전달할 핵심 메시지 (1문장)

## 2. Main Subject (주요 피사체)
- **description**: 무엇을 보여줄 것인가 (구체적 묘사)
- **position**: 화면 내 위치 (center, left-third, right-third)
- **size**: 화면 내 크기 (large, medium, small)

## 3. Background (배경)
- **type**: solid, gradient, image, blurred
- **description**: 배경 설명 (색상, 분위기 등)
- **effects**: [blur, vignette, glow, noise 등]

## 4. Elements (구성 요소들)
각 요소별:
- **type**: text, icon, graphic, shape
- **content**: 구체적 내용
- **position**: 배치 위치
- **style**: 시각적 스타일

## 5. Camera (카메라 설정)
- **angle**: eye-level, high-angle, low-angle, dutch-angle
- **shot_type**: extreme-close-up, close-up, medium-shot, wide-shot
- **lighting**: dramatic, soft, natural, neon, studio
- **depth_of_field**: shallow, medium, deep

## 6. Style (스타일)
- photorealistic, illustration, 3D-render, vector-art, mixed-media 등

## 7. Mood (분위기)
- energetic, calm, mysterious, professional, playful 등

## 8. Color Palette (색상 팔레트)
- **primary**: 주요 색상 [hex 코드 2-3개]
- **accent**: 강조 색상 [hex 코드 1-2개]
- **text**: 텍스트 색상 [hex 코드 1개]

## 9. Avoid (피해야 할 요소)
- Semantic negative prompts (구체적으로 무엇을 피할지)

# Guidelines

## Visual Strategy 원칙
1. **Hyper-Specific**: 모호한 표현 금지, 구체적 묘사
2. **Context First**: 전체 맥락을 먼저 설정한 후 디테일 추가
3. **Semantic Negatives**: "not", "without" 같은 단어 피하고, 원하는 결과를 긍정적으로 표현

## Title Style별 비주얼 가이드

**Avoidance (회피형)**
- 경고 요소 포함 (느낌표, 경고 표시 등)
- 대비 강한 색상 (빨강, 노랑)
- 긴장감 있는 구도

**Result (결과형)**
- Before/After 암시
- 화살표, 변화 표현
- 명확한 구조

**Number (숫자형)**
- 숫자 강조 (크게, 굵게)
- 리스트 구조 암시
- 정돈된 레이아웃

**Secret (비밀형)**
- 어두운 배경 + 스포트라이트
- 신비로운 분위기
- 일부 숨김 효과

**Verify (검증형)**
- 비교 구조 (vs, 대결)
- 체크마크, X표 활용
- 중립적 색상

# Output Format
반드시 JSON 형식으로 반환하세요:

```json
{
  "purpose": "...",
  "main_subject": {
    "description": "...",
    "position": "...",
    "size": "..."
  },
  "background": {
    "type": "...",
    "description": "...",
    "effects": [...]
  },
  "elements": [
    {
      "type": "...",
      "content": "...",
      "position": "...",
      "style": "..."
    }
  ],
  "camera": {
    "angle": "...",
    "shot_type": "...",
    "lighting": "...",
    "depth_of_field": "..."
  },
  "style": "...",
  "mood": "...",
  "color_palette": {
    "primary": ["#...", "#..."],
    "accent": ["#..."],
    "text": "#..."
  },
  "avoid": "..."
}
```
"""

    def __init__(self):
        """Visual Director Agent 초기화"""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"
        self.temperature = 0.7
        self.max_tokens = 1500
        
        logger.info(f"VisualDirectorAgent 초기화 완료 (model={self.model})")
    
    async def create_visual_strategy(
        self,
        headline: Dict,
        keywords: List[str],
        script_summary: str,
        image_refs: Optional[Dict] = None
    ) -> Dict:
        """
        Visual Strategy 생성
        
        Args:
            headline: 선택된 제목
                {
                    "main_title": "AI 칩 전쟁",
                    "sub_title": "삼성이 반격한다",
                    "style_type": "secret",
                    "keywords_used": ["AI 반도체", "삼성전자"]
                }
            keywords: 키워드 리스트
            script_summary: 스크립트 요약
            image_refs: 이미지 레퍼런스 (옵션)
                {
                    "ref_layout": "layout_001.jpg",
                    "ref_person": "person_001.jpg",
                    "ref_asset": "asset_001.png",
                    "ref_style": "style_001.jpg"
                }
        
        Returns:
            Dict: Visual Strategy
                {
                    "purpose": "...",
                    "main_subject": {...},
                    "background": {...},
                    "elements": [...],
                    "camera": {...},
                    "style": "...",
                    "mood": "...",
                    "color_palette": {...},
                    "avoid": "...",
                    "image_refs": {...}
                }
        
        Raises:
            ValueError: 필수 입력이 없는 경우
            Exception: LLM API 호출 실패
        """
        # 입력 검증
        if not headline:
            raise ValueError("제목 정보가 없습니다")
        
        if not headline.get("main_title"):
            raise ValueError("메인 제목이 없습니다")
        
        # 사용자 프롬프트 생성
        user_prompt = self._create_user_prompt(
            headline=headline,
            keywords=keywords,
            script_summary=script_summary,
            image_refs=image_refs
        )
        
        logger.info(f"Visual Strategy 생성 시작: {headline['main_title']}")
        
        try:
            # GPT-4o 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 응답 파싱
            content = response.choices[0].message.content.strip()
            
            # JSON 추출
            visual_strategy = self._parse_response(content)
            
            # 이미지 레퍼런스 추가
            if image_refs:
                visual_strategy["image_refs"] = image_refs
            
            logger.info(f"Visual Strategy 생성 완료: {headline['main_title']}")
            
            return visual_strategy
            
        except Exception as e:
            logger.error(f"Visual Strategy 생성 실패: {e}")
            raise Exception(f"Visual Strategy 생성 실패: {e}")
    
    def _create_user_prompt(
        self,
        headline: Dict,
        keywords: List[str],
        script_summary: str,
        image_refs: Optional[Dict]
    ) -> str:
        """사용자 프롬프트 생성"""
        
        # 제목 정보
        title_info = f"""# 선택된 제목
**Main Title**: {headline.get('main_title')}
**Sub Title**: {headline.get('sub_title')}
**Style Type**: {headline.get('style_type')}
**Keywords Used**: {', '.join(headline.get('keywords_used', []))}
"""
        
        # 키워드
        keywords_info = f"""# 키워드
{', '.join(keywords)}
"""
        
        # 스크립트 요약
        summary_info = f"""# 스크립트 요약
{script_summary}
"""
        
        # 이미지 레퍼런스
        refs_info = ""
        if image_refs:
            refs_info = f"""# 이미지 레퍼런스
"""
            if image_refs.get("ref_layout"):
                refs_info += f"- 레이아웃 레퍼런스: {image_refs['ref_layout']}\n"
            if image_refs.get("ref_person"):
                refs_info += f"- 인물 사진: {image_refs['ref_person']}\n"
            if image_refs.get("ref_asset"):
                refs_info += f"- 아이콘/오브젝트: {image_refs['ref_asset']}\n"
            if image_refs.get("ref_style"):
                refs_info += f"- 스타일 레퍼런스: {image_refs['ref_style']}\n"
        
        # 전체 프롬프트 조합
        user_prompt = f"""{title_info}

{keywords_info}

{summary_info}

{refs_info}

위 정보를 바탕으로 **Visual Strategy**를 생성하세요.
반드시 JSON 형식으로 반환하세요."""
        
        return user_prompt
    
    def _parse_response(self, content: str) -> Dict:
        """응답 파싱"""
        try:
            # JSON 코드 블록 제거
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # JSON 파싱
            visual_strategy = json.loads(content)
            
            # 필수 필드 검증
            required_fields = [
                "purpose",
                "main_subject",
                "background",
                "elements",
                "camera",
                "style",
                "mood",
                "color_palette",
                "avoid"
            ]
            
            for field in required_fields:
                if field not in visual_strategy:
                    raise ValueError(f"필수 필드 누락: {field}")
            
            return visual_strategy
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}\n응답: {content}")
            raise ValueError(f"JSON 파싱 실패: {e}")
        except Exception as e:
            logger.error(f"응답 파싱 실패: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
