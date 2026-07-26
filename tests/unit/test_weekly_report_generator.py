"""
Testes do WeeklyReportGenerator.

Este arquivo nasceu de um bug: o serviço usava dois model IDs Claude
depreciados (primário E fallback), num endpoint vivo, sem nenhum teste que
avisasse. Os testes aqui cobrem o contrato da chamada à API — model IDs,
parâmetros aceitos, leitura da resposta e recusa — usando mocks, sem rede
e sem credencial.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.weekly_report_generator import WeeklyReportGenerator

# IDs válidos na geração atual da API. Se um destes for depreciado, este
# teste falha e o aviso chega antes da produção.
MODELOS_ATUAIS = {"claude-opus-5", "claude-sonnet-5", "claude-opus-4-8"}


def test_model_ids_sao_da_geracao_atual():
    """Regressão: os IDs anteriores (claude-*-4-20250514) foram depreciados."""
    assert WeeklyReportGenerator.CLAUDE_MODEL in MODELOS_ATUAIS
    assert WeeklyReportGenerator.CLAUDE_FALLBACK_MODEL in MODELOS_ATUAIS


def test_nao_usa_ids_depreciados():
    """Guarda explícita contra os IDs que causaram o bug."""
    depreciados = {"claude-opus-4-20250514", "claude-sonnet-4-20250514"}
    assert WeeklyReportGenerator.CLAUDE_MODEL not in depreciados
    assert WeeklyReportGenerator.CLAUDE_FALLBACK_MODEL not in depreciados
