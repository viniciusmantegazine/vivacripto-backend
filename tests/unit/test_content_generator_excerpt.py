"""
Testes do _generate_excerpt: o texto do primeiro H2 vazava no excerpt
(o código antigo só removia os caracteres '##', não a linha de heading).
"""
import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.mark.asyncio
async def test_excerpt_ignora_linha_de_heading():
    gen = ContentGenerator()
    content = (
        "## Manchete Interna do Artigo\n\n"
        "O Bitcoin subiu nesta terça-feira. Investidores acompanham o movimento. "
        "Uma terceira frase que não deve entrar."
    )

    excerpt = await gen._generate_excerpt(content)

    assert "Manchete" not in excerpt
    assert excerpt.startswith("O Bitcoin subiu")


@pytest.mark.asyncio
async def test_excerpt_remove_negrito_e_limita_150():
    gen = ContentGenerator()
    content = "## Titulo\n\n**Bitcoin** " + ("palavra " * 40) + ". Segunda frase."

    excerpt = await gen._generate_excerpt(content)

    assert "**" not in excerpt
    assert len(excerpt) <= 150
