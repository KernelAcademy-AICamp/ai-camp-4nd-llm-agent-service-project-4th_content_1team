# /error Command

에러 메시지를 분석하는 커맨드입니다.

## 사용법
```
/error <에러 메시지 또는 스택 트레이스>
```

## 동작
이 커맨드가 실행되면 다음을 수행합니다:

1. **senior-error-analyst 에이전트 호출**
   - Task tool을 사용하여 `senior-error-analyst` 서브에이전트를 실행
   - 사용자가 입력한 에러 내용을 분석

2. **분석 범위**
   - 에러 메시지 및 스택 트레이스 분석
   - 관련 코드 파일 확인
   - 외부 API 에러의 경우 WebSearch로 공식 문서 검색
   - 파라미터 호환성 및 제약사항 검증

3. **Skills 참조 (필수)**
   - `.claude/skills/` 폴더의 관련 skill 파일 확인
   - 프로젝트별 규칙 및 가이드라인 적용

## 실행 지침

사용자가 `/error` 커맨드를 실행하면:

```
Task tool 호출:
- subagent_type: senior-error-analyst
- prompt: |
    ## 에러 분석 요청

    ### 에러 내용
    $ARGUMENTS

    ### 분석 지침
    1. 에러 메시지와 스택 트레이스 분석
    2. 관련 코드 파일을 Read tool로 확인
    3. 외부 API 에러인 경우 WebSearch로 공식 문서 검색 (필수)
    4. 파라미터 호환성 및 API 제약사항 검증
    5. `.claude/skills/` 폴더의 관련 skill 확인
    6. 구체적인 해결 방안 제시

    ### 프로젝트 컨텍스트
    - 프로젝트 경로: C:\Users\talls\Desktop\noonaProject\youtube-maker
    - 백엔드: BE/ 폴더 (Python/FastAPI)
    - Skills 위치: .claude/skills/
```

## 예시

### 입력
```
/error TypeError: cannot unpack non-iterable NoneType object at line 45
```

### 출력
senior-error-analyst가 에러를 분석하고:
- 에러 요약
- 원인 분석 (직접적/근본적)
- 해결 방안 (즉시/장기)
- 검증 방법
을 제공합니다.

## 관련 리소스
- Agent: `.claude/agents/senior-error-analyst.md`
- Skills: `.claude/skills/`
