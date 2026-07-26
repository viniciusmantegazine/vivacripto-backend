"""
Testes do system prompt do relatório semanal.

O parâmetro `temperature=0.7` foi removido (a API atual o rejeita com 400);
a intenção de "análise mais criativa" passou a viver no prompt. Estes testes
garantem que a diretriz existe e que ela não afrouxa os guardrails.
"""
from app.services.ai.prompts.weekly_report_prompts import WEEKLY_REPORT_SYSTEM_PROMPT


def test_tem_diretriz_de_voz_analitica():
    """Substitui o temperature removido — sem ela o tom fica ao acaso."""
    assert "<voz_analitica>" in WEEKLY_REPORT_SYSTEM_PROMPT
    assert "</voz_analitica>" in WEEKLY_REPORT_SYSTEM_PROMPT


def test_diretriz_de_tom_nao_afrouxa_os_guardrails():
    """
    A instrução de tom não pode virar licença para inventar dado ou dar
    conselho de investimento — ela reafirma os limites explicitamente.
    """
    inicio = WEEKLY_REPORT_SYSTEM_PROMPT.index("<voz_analitica>")
    fim = WEEKLY_REPORT_SYSTEM_PROMPT.index("</voz_analitica>")
    bloco = WEEKLY_REPORT_SYSTEM_PROMPT[inicio:fim].lower()

    assert "não inventar dados" in bloco
    assert "conselho de investimento" in bloco
    assert "prever preços" in bloco
