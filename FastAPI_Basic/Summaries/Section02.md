# Section 02. FastAPI 알아보기

## 기본 설정

Ubuntu desktop OS, PyCharm을 사용해 실습을 진행한다. 먼저 프로젝트를 생성하고 FastAPI를 사용하기 위해 필요한 패키지들을 설치한다.

```
$ sudo apt-get update -y
$ sudo apt-get upgrade -y
$ sudo apt-get install python3.10 python3.10-venv python3.10-dev
$ pip install fastapi
$ pip install uvicorn
```

그 다음 `python3.10 -m venv [Project name]` 명령어로 가상환경을 생성하고, 해당 디렉터리로 이동해 `source bin/activate`로 가상환경을 활성화한다.

마지막으로 Pycharm에서 해당 디렉터리를 기준으로 프로젝트를 열고 하위 디렉터리로 **src**를 생성한 후 **Mark Directory as > Sources Root**로 소스 디렉터리로 지정한다.

![Mark Directory as Sources Root](Images/image1.png)

## 첫 번째 API 작성

이제 FastAPI를 사용해 첫 번째 API를 작성해 보자.

**src/main.py**

```
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check_handler():
    return { "ping": "pong" }
```

서버 배포 시 서버가 살아있는지 확인하기 위한 헬스체크 API를 만들었다. 다른 백엔드 프레임워크들과 비슷하게 데코레이터로 API 경로를 명시하고 핸들러 함수를 정의한다.

이제 터미널에서 **src** 디렉터리로 이동해 `uvicorn main:app`으로 애플리케이션을 실행하면 기본적으로 8000번 포트에서 서버가 실행된다.

```
src$ uvicorn main:app
INFO:     Started server process [579543]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

해당 경로로 접속하면 헬스체크 핸들러의 JSON 형식 응답을 확인할 수 있고, **origin/docs** 경로로 이동하면 자동 생성된 API 문서를 확인할 수 있다.

![Auto generated API docs](Images/image2.png)
