"""
CopywriterAgent - 제목 생성 에이전트

GPT-4o mini를 사용하여 심리 전략 기반 제목 세트 3개를 생성합니다.
"""
import logging
import json
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from openai import AsyncOpenAI

from app.core.config import settings


logger = logging.getLogger(__name__)


# 시스템 프롬프트
SYSTEM_PROMPT = """# Role
당신은 유튜브 썸네일 카피라이팅 전문가입니다.
클릭률(CTR)을 극대화하는 임팩트 있는 제목을 작성하는 것이 당신의 임무입니다.

# Task
주어진 맥락과 키워드를 바탕으로 **정확히 3개의 제목 세트**를 생성하세요.

# Title Structure
각 제목 세트는 다음 구조를 따릅니다:

- **Main Title**: 메인 제목 (10자 이내)
  - 강렬하고 임팩트 있는 핵심 메시지
  - 궁금증을 유발하는 표현

- **Sub Title**: 서브 제목 (15자 이내)
  - Main Title을 보완하는 부가 정보
  - 구체적인 내용 암시

# Title Styles
반드시 서로 다른 스타일로 3개를 생성하세요:

1. **Avoidance (회피형)**
   - "모르면 손해", "이것만은 피하세요", "절대 하지 마세요"
   - 심리: 손실 회피 심리 자극

2. **Result (결과형)**
   - "~의 결과는?", "~하면 일어나는 일", "~의 진실"
   - 심리: 결과에 대한 호기심

3. **Number (숫자형)**
   - "TOP 3", "5가지 방법", "7일 만에"
   - 심리: 구체성과 완결성

4. **Secret (비밀형)**
   - "숨겨진 진실", "공개되지 않은", "알려지지 않은"
   - 심리: 내부자 정보 욕구

5. **Verify (검증형)**
   - "사실일까?", "진짜 vs 가짜", "팩트체크"
   - 심리: 진위 확인 욕구

# Guidelines
- Main Title: 최대한 짧고 강렬하게 (이모지 사용 금지)
- Sub Title: Main Title을 보완하되 반복 피하기
- 키워드 자연스럽게 포함 (억지로 모든 키워드 사용 X)
- 과장된 표현 주의 (예: "충격", "경악", "실화")
- 문장 끝에 느낌표 지양 (임팩트는 내용으로)

# Output Format
JSON 형식으로 반환하세요:

```json
{
  "title_sets": [
    {
      "id": 1,
      "main_title": "메인 제목",
      "sub_title": "서브 제목",
      "style_type": "avoidance",
      "keywords_used": ["키워드1", "키워드2"],
      "rationale": "이 제목을 선택한 이유 (2-3문장)"
    }
  ]
}
```
"""


class CopywriterAgent:
    """
    제목 생성 에이전트
    
    GPT-4o mini를 사용하여 심리 전략 기반 제목 세트 3개를 생성합니다.
    
    Example:
        >>> copywriter = CopywriterAgent()
        >>> title_sets = await copywriter.generate_headlines(
        ...     keywords=["AI 반도체", "엔비디아"],
        ...     script_summary="AI 반도체 시장 분석"
        ... )
        >>> print(title_sets[0]["main_title"])
        'AI 칩 전쟁'
    """
    
    def __init__(
        self, 
        model: str = "gpt-4o-mini",
        temperature: float = 0.8,
        max_tokens: int = 500
    ):
        """
        CopywriterAgent 초기화
        
        Args:
            model: 사용할 LLM 모델 (기본값: "gpt-4o-mini")
            temperature: 창의성 수준 (기본값: 0.8)
            max_tokens: 최대 토큰 수 (기본값: 500)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.logger = logger
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(ValueError)  # ValueError는 재시도하지 않음
    )
    async def generate_headlines(
        self,
        keywords: List[str],
        script_summary: str,
        script_chunks: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        제목 세트 3개 생성
        
        Args:
            keywords: 사용자가 선택한 키워드 리스트
            script_summary: 스크립트 요약
            script_chunks: 청킹된 스크립트 (선택사항)
            
        Returns:
            List[Dict]: 제목 세트 3개
                [
                    {
                        "id": 1,
                        "main_title": "AI 칩 전쟁",
                        "sub_title": "삼성이 반격한다",
                        "style_type": "secret",
                        "keywords_used": ["AI 반도체", "삼성전자"],
                        "rationale": "비밀형 스타일로..."
                    },
                    ...
                ]
        
        Raises:
            ValueError: 키워드가 비어있거나 요약이 없는 경우
            Exception: LLM API 호출 실패
        """
        # 입력 검증
        if not keywords or len(keywords) == 0:
            raise ValueError("키워드가 비어있습니다")
        
        if not script_summary:
            raise ValueError("스크립트 요약이 비어있습니다")
        
        self.logger.info(f"제목 생성 시작 (키워드: {len(keywords)}개)")
        
        try:
            # 사용자 프롬프트 생성
            user_prompt = self._create_user_prompt(
                keywords, 
                script_summary, 
                script_chunks
            )
            
            # LLM 호출
            response = await self._call_llm(user_prompt)
            
            # 응답 파싱
            title_sets = self._parse_response(response)
            
            # 검증
            if len(title_sets) != 3:
                raise ValueError(f"제목 세트 개수가 3개가 아닙니다: {len(title_sets)}개")
            
            self.logger.info(f"제목 생성 완료: {len(title_sets)}개")
            return title_sets
        
        except Exception as e:
            self.logger.error(f"제목 생성 실패: {e}")
            raise
    
    def _create_user_prompt(
        self,
        keywords: List[str],
        script_summary: str,
        script_chunks: Optional[List[Dict]] = None
    ) -> str:
        """
        사용자 프롬프트 생성
        
        Args:
            keywords: 키워드 리스트
            script_summary: 스크립트 요약
            script_chunks: 청킹된 스크립트
            
        Returns:
            str: 사용자 프롬프트
        """
        prompt_parts = []
        
        # 맥락 (청킹된 스크립트 또는 요약)
        prompt_parts.append("# 맥락 (Context)")
        if script_chunks:
            for chunk in script_chunks[:3]:  # 최대 3개
                prompt_parts.append(f"\n[{chunk.get('title', '섹션')}]")
                prompt_parts.append(chunk.get('content', '')[:200] + "...")
        else:
            prompt_parts.append(f"\n{script_summary}")
        
        # 선택된 키워드
        prompt_parts.append(f"\n\n# 선택된 키워드")
        prompt_parts.append(f"{', '.join(keywords)}")
        
        # 지시사항
        prompt_parts.append("\n\n# 지시사항")
        prompt_parts.append("위 맥락과 키워드를 바탕으로 제목 세트 3개를 생성하세요.")
        prompt_parts.append("반드시 JSON 형식으로만 응답하세요.")
        
        return "\n".join(prompt_parts)
    
    async def _call_llm(self, user_prompt: str) -> str:
        """
        LLM API 호출
        
        Args:
            user_prompt: 사용자 프롬프트
            
        Returns:
            str: LLM 응답
        """
        self.logger.info(f"LLM 호출 시작 (모델: {self.model})")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        self.logger.info("LLM 호출 완료")
        
        return content
    
    def _parse_response(self, response: str) -> List[Dict]:
        """
        LLM 응답 파싱
        
        Args:
            response: LLM 응답 (JSON 문자열)
            
        Returns:
            List[Dict]: 제목 세트 리스트
        """
        try:
            data = json.loads(response)
            title_sets = data.get("title_sets", [])
            
            # 필수 필드 검증
            for title_set in title_sets:
                required_fields = [
                    "id", "main_title", "sub_title", 
                    "style_type", "keywords_used", "rationale"
                ]
                for field in required_fields:
                    if field not in title_set:
                        raise ValueError(f"필수 필드 누락: {field}")
            
            return title_sets
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {response[:100]}...")
    
    def get_model_info(self) -> Dict:
        """
        모델 정보 반환
        
        Returns:
            Dict: 모델 정보
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
