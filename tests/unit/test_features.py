import numpy as np
from sklearn.pipeline import Pipeline

from src.ml.features import build_feature_pipeline, create_sequences


def test_create_sequences():
    # Criar dados sintéticos: 100 timesteps, 5 features
    data = np.random.rand(100, 5)
    time_steps = 10

    X, y = create_sequences(data, time_steps=time_steps)

    # 100 - 10 = 90 amostras
    assert X.shape == (90, 10, 5)
    assert y.shape == (90,)

    # O y da primeira amostra deve ser a primeira feature (index 0)
    # do dado no índice 'time_steps'
    assert y[0] == data[time_steps, 0]


def test_build_feature_pipeline():
    pipeline = build_feature_pipeline()
    assert isinstance(pipeline, Pipeline)
    # Verificar se o último passo é o selector (o scaler é aplicado posteriormente)
    assert pipeline.steps[-1][0] == "selector"
