# 아트메이트(ArtMate)

2022 개정 미술과 교육과정 기반 초·중등 미술 학습 도우미입니다. Windows PowerShell 기준입니다.

## 1. 설치

가상환경은 PC마다 따로 만듭니다(OneDrive로 공유한 venv는 다른 PC에서 실행되지 않습니다). 예: 연구실 PC는 `venv-lab`.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. 설정

`.env.example`을 `.env`로 복사한 뒤 키를 넣습니다.

```
GOOGLE_API_KEY=발급받은 Gemini API 키
TAVILY_API_KEY=발급받은 타빌리 API 키
```

## 3. 교육과정 인덱스 구축 (처음 1회)

국가교육과정정보센터(NCIC)에서 내려받은 2022 개정 미술과 교육과정 PDF를 `data/raw/교육과정.pdf`로 둔 뒤 실행합니다.

```powershell
python -m scripts.build_index
```

## 4. 실행

```powershell
streamlit run app.py
```

## 5. 테스트

```powershell
pytest
```

## 6. 배포 (Streamlit Community Cloud)

`main`에 푸시하면 자동으로 다시 배포됩니다. API 키는 앱 설정의 Secrets에 넣습니다.

```toml
GOOGLE_API_KEY = "발급받은 Gemini API 키"
TAVILY_API_KEY = "발급받은 타빌리 API 키"
```
