# PythonAnywhere 배포/운영 체크리스트

이 앱은 Flask + SQLite 앱입니다. 운영 데이터는 GitHub가 아니라 PythonAnywhere 서버의 `instance/workout.db`에 저장됩니다.

## 최초 배포

```bash
git clone https://github.com/rlalastjd782-oss/serviceproject.git
cd serviceproject
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

PythonAnywhere `Web` 탭에서 Manual configuration 앱을 만들고 Virtualenv를 아래처럼 지정합니다.

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/.venv
```

WSGI 파일은 아래 형태로 맞춥니다.

```python
import sys

PROJECT_DIR = "/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app as application
```

Static files 설정:

```text
URL: /static/
Directory: /home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/static
```

## 업데이트 배포

로컬에서 작업 후 push가 끝난 상태에서 PythonAnywhere Bash 콘솔에서 실행합니다.

```bash
cd ~/serviceproject
bash deploy_pythonanywhere.sh
```

이 스크립트는 `git pull`, 패키지 설치 확인, WSGI reload까지 한 번에 처리합니다.
첫 실행 때 권한을 주고 싶으면 아래처럼 실행해도 됩니다.

```bash
chmod +x deploy_pythonanywhere.sh
./deploy_pythonanywhere.sh
```

문제가 생기면 수동으로 아래 명령을 실행한 뒤 PythonAnywhere `Web` 탭에서 `Reload`를 누릅니다.

```bash
cd ~/serviceproject
git pull origin master
source .venv/bin/activate
pip install -r requirements.txt
touch /var/www/kimmins_pythonanywhere_com_wsgi.py
```

## 배포 전 확인

- 로컬에서 `python -m unittest discover -s tests` 통과
- 로컬에서 `node --check static/app.js` 통과
- GitHub에 최신 커밋 push 완료
- 설정 화면에서 JSON 백업 다운로드
- PythonAnywhere에서 `bash deploy_pythonanywhere.sh` 실행
- 모바일에서 새로고침 후 버전 표시 변경 확인

## 데이터 백업 위치

운영 DB:

```text
/home/YOUR_PYTHONANYWHERE_USERNAME/serviceproject/instance/workout.db
```

앱 설정 화면에서 받을 수 있는 백업:

- JSON 전체 백업
- 운동 CSV
- 식단 CSV

삭제/복원 작업 전에는 앱이 `instance/delete_backups` 또는 `instance/restore_backups`에 백업을 남기도록 되어 있습니다.

## 모바일 캐시 주의

앱은 PWA 캐시를 사용합니다. 배포 후 화면이 예전 버전처럼 보이면 아래 순서로 확인합니다.

1. 브라우저 새로고침
2. 모바일 브라우저 탭 닫고 다시 접속
3. 홈 화면에 설치한 앱이면 앱을 완전히 종료 후 재실행
4. 그래도 안 바뀌면 홈 화면 바로가기를 삭제 후 다시 설치

헤더의 버전 표시가 최신 커밋으로 바뀌면 새 코드가 반영된 상태입니다.
