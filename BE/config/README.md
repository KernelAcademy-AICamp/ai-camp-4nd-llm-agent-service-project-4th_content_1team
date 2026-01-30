# YouTube Cookies 디렉토리

## 용도
YouTube 자막 다운로드 시 429 에러 방지를 위한 Cookies 파일 저장

## 파일
- `youtube_cookies.txt` - YouTube 로그인 Cookies (Netscape 형식)

## 설정 방법

1. Chrome 확장 프로그램 설치: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. YouTube 로그인
3. 확장 프로그램에서 Cookies 내보내기
4. 이 디렉토리에 `youtube_cookies.txt`로 저장
5. `.env` 파일에 `YOUTUBE_COOKIES_FILE=config/youtube_cookies.txt` 추가

## 보안
⚠️ **이 파일을 절대 Git에 커밋하지 마세요!**
- .gitignore에 이미 추가되어 있습니다
- 개인 로그인 정보가 포함되어 있습니다
