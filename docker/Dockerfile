FROM python:3.11-slim

# Evita que o Python escreva arquivos .pyc e força flush imediato dos logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Instala dependências de sistema necessárias para compilar pacotes C e manipular rede
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte e arquivos de configuração
COPY . .

# Cria pasta de downloads locais para o ETL
RUN mkdir -p /app/autocub_downloads

EXPOSE 8002

CMD ["uvicorn", "autocub.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
