FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY entropy-publisher-mock.py __init__.py ./

USER 65534:65534

CMD ["python", "entropy-publisher-mock.py", "--host", "mosquitto", "--port", "1883", "--channels", "1-2", "--rate", "184", "--increment-ps", "5430000000", "--jitter-ps", "2715000000"]
