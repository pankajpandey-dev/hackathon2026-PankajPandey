# ShopWave FastAPI app — repo root must contain data/, audit_logs/, frontend/, and app/
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/work/app

WORKDIR /work/app

COPY requirements.txt /work/requirements.txt
RUN pip install --upgrade pip && pip install -r /work/requirements.txt

# Application code and runtime assets (paths expected by app/core/config.py)
COPY app/ /work/app/
COPY data/ /work/data/
COPY frontend/ /work/frontend/
# audit_logs/ is gitignored (generated at runtime); empty dir is enough for the API
RUN mkdir -p /work/audit_logs

EXPOSE 8000

# REPO_ROOT resolves to /work (three levels above app/core/config.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
