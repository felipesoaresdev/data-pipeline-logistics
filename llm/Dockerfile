# Usar uma imagem base com Python
FROM python:3.11-slim

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiar os arquivos do diretório atual para o contêiner
COPY . .

# Adiciona a raiz da aplicação ao PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Instalar dependências, se o arquivo requirements.txt existir
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Comando padrão para rodar o script
CMD ["python", "-u", "agente_categorizacao.py"]
