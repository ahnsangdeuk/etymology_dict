# 영어 어원 사전 (Etymology Dictionary) v1.0

Free Dictionary API를 활용한 영어 단어 검색 및 학습 도구입니다.

## 주요 기능

1. 단어 검색
   - 발음 기호 표시
   - 발음 듣기 (TTS)
   - 품사별 의미
   - 예문
   - 동의어/반의어
   - 어원 정보

2. 번역 기능
   - 영어 원문 우선 표시
   - 필요 시 한국어 번역
   - 번역 시 원문 함께 표시

3. 단어장
   - 단어 저장
   - 노트 기능
   - 발음 듣기
   - 번역 기능

## 기술 스택

- Backend: Flask, SQLAlchemy
- Frontend: Bootstrap 5
- APIs:
  - Free Dictionary API (단어 정보)
  - Google Translate API (번역)
  - gTTS (Text-to-Speech)

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 애플리케이션 실행:
```bash
python app.py
```

## 버전 히스토리

### v1.0 (2024-12-12)
- 초기 버전 릴리스
- Free Dictionary API 연동
- 단어 검색 및 단어장 기능
- 발음 듣기 기능
- 번역 기능 