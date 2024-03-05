FROM python:3.12-slim
WORKDIR /datoso

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/datoso/venv/bin:$PATH"
RUN python -m venv venv
RUN . venv/bin/activate
RUN pip install --upgrade pip
RUN pip install setuptools
RUN pip install datoso[all]

ENTRYPOINT ["datoso"]
