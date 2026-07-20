# O .PHONY garante que o comando rode mesmo que exista um ficheiro com o mesmo nome na pasta
.PHONY: install format test run train promote clean start stop

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
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

train:
	@echo "Iniciando o pipeline de otimização e treino do modelo LSTM..."
	uv run python -m src.pipelines.tune_pipeline

promote:
	@echo "Executando o script de promoção de modelos Challenger/Champion baseados em RMSE..."
	uv run python -m src.pipelines.promote_model

inference:
	@echo "Executando o script de inferência..."
	uv run python -m src.ml.inference

clean:
	@echo "Limpando ficheiros temporários, cache e artefatos de Python..."
	uv run python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.pytest_cache') if p.is_dir()]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.ruff_cache') if p.is_dir()]; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc') if p.is_file()]"

start:
	@echo "Iniciando a infraestrutura local (MinIO, PostgreSQL, etc.)..."
	docker-compose up -d

stop:
	@echo "Parando e destruindo a infraestrutura local..."
	docker-compose down
