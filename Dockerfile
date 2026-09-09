FROM node:23-slim AS ui

WORKDIR /ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# One image serves three roles -- the API/UI, the Kubernetes operator
# (`python -m controller`), and the reload sidecar (`python -m
# controller.reloader`) -- so it carries the operator dependencies too. They
# share a version, which is what keeps the rendered config identical no matter
# which of them wrote it.
COPY requirements.txt requirements-operator.txt ./
RUN pip install --no-cache-dir -r requirements-operator.txt

COPY app/ ./app/
COPY cli/ ./cli/
COPY controller/ ./controller/

# The compiled SPA is served at / by the backend. Set SERVE_UI=false to run
# the API on its own.
COPY --from=ui /ui/dist ./app/static

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
