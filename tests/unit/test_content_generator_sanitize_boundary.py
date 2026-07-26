"""
Testes de fronteira de palavra na remoção de nomes de veículos.

Bug corrigido aqui: a lista de veículos tinha variantes em minúscula
("decrypt", "the block") e o casamento era por substring, então
vocabulário técnico normal era tratado como nome de veículo. Medido no
código anterior:

    "A transação foi decrypted pelo protocolo."  -> "A transação foi ed ..."
    "Dados via the blockchain publica."          -> "Dados via chain publica."

O mesmo defeito emitia "[Sanitização CRÍTICA] LLM violou regra e citou
veículo 'decrypt'" quando o LLM não havia citado nada.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


# --- Grupo 1: vocabulário técnico deve sair intacto -------------------------

@pytest.mark.parametrize(
    "texto",
    [
        "A transação foi decrypted pelo protocolo de rede.",
        "O processo de decryption garante privacidade ao usuário.",
        "Dados armazenados on-chain via the blockchain publica.",
        "Analistas avaliam the block height atual da rede Bitcoin.",
    ],
)
def test_vocabulario_tecnico_nao_e_corrompido(generator: ContentGenerator, texto: str):
    """
    Regressão: substring fazia "decrypt" casar dentro de "decrypted" e
    "the block" dentro de "the blockchain".

    O caso "the block height" só passa por causa da exceção case-sensitive
    de `The Block` — fronteira de palavra sozinha não resolve esse.
    """
    assert generator._sanitize_content(texto) == texto


# --- Grupo 2: citação real de veículo deve ser removida --------------------

@pytest.mark.parametrize(
    "texto,proibido",
    [
        ("Segundo o CoinDesk, o Bitcoin subiu forte.", "CoinDesk"),
        ("The Block informou que houve um incidente.", "The Block"),
        ("Conforme o Decrypt, a rede ficou instável.", "Decrypt"),
        ("segundo o cointelegraph, houve queda no volume.", "cointelegraph"),
    ],
)
def test_citacao_de_veiculo_continua_removida(
    generator: ContentGenerator, texto: str, proibido: str
):
    """A correção não pode afrouxar o propósito original da sanitização."""
    resultado = generator._sanitize_content(texto)

    assert proibido.lower() not in resultado.lower()


# --- Grupo 3: provedores de dados são permitidos --------------------------

@pytest.mark.parametrize(
    "provedor",
    ["CoinGecko", "Glassnode", "Chainalysis"],
)
def test_provedores_de_dados_nao_sao_removidos(
    generator: ContentGenerator, provedor: str
):
    """
    O prompt permite explicitamente provedores de DADOS (não são veículos
    jornalísticos). Guarda contra alguém adicioná-los à lista por engano.
    """
    texto = f"Dados da {provedor} mostram alta no volume negociado."

    assert provedor in generator._sanitize_content(texto)


# --- Grupo 4: invariantes da configuração --------------------------------

def test_lista_de_veiculos_nao_tem_duplicata_de_caixa():
    """
    As variantes de caixa existiam só porque a remoção era case-sensitive.
    Com regex + re.IGNORECASE elas são redundantes, e reintroduzi-las
    ressuscitaria a confusão que causou o bug.
    """
    nomes = list(ContentGenerator.SOURCE_SITE_NAMES)
    minusculos = [n.lower() for n in nomes]

    assert len(minusculos) == len(set(minusculos)), (
        f"duplicata de caixa na lista: {nomes}"
    )


def test_excecao_case_sensitive_esta_documentada():
    """
    `The Block` casa case-sensitive porque "the block" é vocabulário cripto
    comum. Este teste impede que a exceção seja removida por engano num
    refactor futuro, ou estendida sem intenção.
    """
    assert "The Block" in ContentGenerator.CASE_SENSITIVE_SITE_NAMES
    assert "CoinDesk" not in ContentGenerator.CASE_SENSITIVE_SITE_NAMES
    # Todo nome da exceção precisa existir na lista principal
    assert ContentGenerator.CASE_SENSITIVE_SITE_NAMES.issubset(
        set(ContentGenerator.SOURCE_SITE_NAMES)
    )
