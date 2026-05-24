# PythonAnywhere 배포 안내

이 앱은 Flask + SQLite 앱입니다. PythonAnywhere에서는 Flask 앱을 Web 탭의 WSGI 설정으로 실행합니다.

## 1. PythonAnywhere에서 저장소 받기

PythonAnywhere Bash 콘솔에서 실행합니다.

```bash
git clone https://github.com/rlalastjd782-oss/serviceproject.git
cd serviceproject
```

## 2. 가상환경 만들기

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Web 앱 생성

PythonAnywhere 상단 메뉴에서 `Web`으로 이동합니다.

1. `Add a new web app`
2. 도메인은 기본값 사용
3. `Manual configuration` 선택
4. Python 버전 선택

## 4. Virtualenv 설정

Web 탭의 `Virtualenv` 항목에 아래 경로를 입력합니다.

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/.venv
```

`YOUR_PYTHONANYWHERE_USERNAME`은 PythonAnywhere 계정명으로 바꿔야 합니다.

## 5. WSGI 파일 수정

Web 탭에서 `WSGI configuration file`을 엽니다. 기존 내용을 지우고 아래처럼 입력합니다.

```python
import os
import sys

PROJECT_DIR = "/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app as application
```

계정명을 실제 PythonAnywhere 계정명으로 바꿉니다.

## 6. 정적 파일 설정

Web 탭의 `Static files`에 아래 항목을 추가합니다.

```text
URL: /static/
Directory: /home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/static
```

## 7. Reload

Web 탭에서 `Reload`를 누릅니다.

이후 아래 주소로 접속합니다.

```text
https://YOUR_PYTHONANYWHERE_USERNAME.pythonanywhere.com
```

## 데이터 저장 위치

SQLite DB는 서버의 아래 파일에 저장됩니다.

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/instance/workout.db
```

이 파일은 GitHub에 올라가지 않습니다. 운영 데이터는 PythonAnywhere 서버 안에만 남습니다.
