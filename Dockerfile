# Usa uma imagem oficial do Python
FROM python:3.11

# Cria a pasta do app dentro do container
WORKDIR /app

# Copia o código pro container
COPY . .

# Instala dependências
RUN pip install -r requirements.txt

# Executa o bot
CMD ["python", "main.py"]