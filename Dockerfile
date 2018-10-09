FROM frolvlad/alpine-python3

LABEL maintainer="Urbano Gutierrez <urbano@fatwhale.io>"

ADD . ./app

WORKDIR /app

RUN apk update && apk upgrade && \
    apk add --no-cache \
    bash \
    git \
    openssh \
    build-base \
    make \
    python3-dev

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
