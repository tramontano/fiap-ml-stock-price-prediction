# O .PHONY garante que o comando rode mesmo que exista um ficheiro com o mesmo nome na pasta
.PHONY: install format test run train clean up down

install:
	@echo "Instalando e sincronizando dependências com o uv..."
	uv sync

format:
	@echo "Formatando o código e corrigindo importações com o ruff..."
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

test:
	@echo "A executar os testes unitários e de integração..."
	uv run pytest tests/ -v

run:
	@echo "Iniciando o servidor FastAPI em modo de desenvolvimento..."
	uv run uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000

train:
	@echo "Iniciando o pipeline de otimização e treino do modelo LSTM..."
	uv run python -m src.pipelines.tune_pipeline

clean:
	@echo "Limpando ficheiros temporários, cache e artefatos de Python..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

up:
	@echo "Iniciando a infraestrutura local (MinIO, PostgreSQL, etc.)..."
	docker-compose up -d

down:
	@echo "Parando e destruindo a infraestrutura local..."
	docker-compose down
