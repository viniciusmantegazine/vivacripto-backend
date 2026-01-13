"""
API News Collector Service
Coleta notícias de APIs externas

Nota: CryptoPanic foi removido por gerar erros 404 frequentes.
Os feeds RSS já cobrem as principais fontes de notícias.
"""
from typing import List, Dict
from loguru import logger


class APICollector:
    """
    Coletor de notícias via APIs externas.

    Atualmente desabilitado pois os feeds RSS cobrem as principais fontes.
    Mantido para extensibilidade futura com outras APIs.
    """

    def __init__(self):
        self.timeout = 10

    async def collect_all(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todas as APIs configuradas.

        Args:
            hours_back: Quantas horas para trás buscar notícias

        Returns:
            Lista de notícias coletadas (vazia - APIs desabilitadas)
        """
        # Nenhuma API externa configurada no momento
        # Os feeds RSS já fornecem cobertura adequada
        logger.debug("APICollector: Nenhuma API externa configurada")
        return []
