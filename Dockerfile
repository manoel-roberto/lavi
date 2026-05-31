FROM python:3.11-slim

# Evita que o Python gere arquivos .pyc e força stdout sem buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Instala dependências de sistema necessárias para rodar o Chromium Headless do Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala apenas o binário Chromium do Playwright
RUN playwright install chromium

# Copia o código da aplicação
COPY . .

# Garante a existência da pasta de dados local
RUN mkdir -p /app/data

# Porta exposta do FastAPI
EXPOSE 8000

# Executa o servidor ASGI do Uvicorn para servir a API e o Frontend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
