"""
Market Data Collector
Coleta dados de mercado em tempo real para enriquecer relatórios semanais.

Fontes:
- CoinGecko: Preços e dados de mercado cripto (gratuito, sem chave)
- Alternative.me: Fear & Greed Index (gratuito, sem chave)
- DuckDuckGo: Busca web para contexto macroeconômico
"""
import asyncio
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger


class MarketDataCollector:
    """
    Coleta dados de mercado em tempo real de APIs públicas e busca na web.
    Todos os dados são formatados como texto para injeção no prompt do Claude.
    """

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"
    FEAR_GREED_URL = "https://api.alternative.me/fng/"

    async def collect_all(self) -> str:
        """
        Coleta todos os dados de mercado e retorna como texto formatado.
        Em caso de falha parcial, retorna o que conseguiu coletar.
        """
        sections = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            crypto = await self._fetch_crypto_prices(client)
            if crypto:
                sections.append(crypto)

            global_data = await self._fetch_global_crypto(client)
            if global_data:
                sections.append(global_data)

            fng = await self._fetch_fear_greed(client)
            if fng:
                sections.append(fng)

        macro = await self._search_macro_context()
        if macro:
            sections.append(macro)

        if not sections:
            return (
                "NOTA: Não foi possível coletar dados de mercado em tempo real. "
                "Use seu conhecimento mais recente e indique explicitamente que "
                "os dados podem estar defasados."
            )

        timestamp = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        header = f"=== DADOS DE MERCADO COLETADOS EM {timestamp} ==="
        return header + "\n\n" + "\n\n".join(sections)

    async def _fetch_crypto_prices(self, client: httpx.AsyncClient) -> Optional[str]:
        """Busca preços de BTC, ETH e principais criptos via CoinGecko"""
        try:
            response = await client.get(
                f"{self.COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": "bitcoin,ethereum,solana,binancecoin,ripple",
                    "order": "market_cap_desc",
                    "sparkline": "false",
                    "price_change_percentage": "24h,7d,30d",
                },
            )
            response.raise_for_status()
            data = response.json()

            lines = ["PREÇOS CRIPTO (fonte: CoinGecko, tempo real):"]
            for coin in data:
                symbol = coin["symbol"].upper()
                price = coin["current_price"]
                mc = coin["market_cap"]
                change_24h = coin.get("price_change_percentage_24h") or 0
                change_7d = coin.get("price_change_percentage_7d_in_currency") or 0
                change_30d = coin.get("price_change_percentage_30d_in_currency") or 0
                ath = coin.get("ath") or 0
                ath_change = coin.get("ath_change_percentage") or 0
                high_24h = coin.get("high_24h") or 0
                low_24h = coin.get("low_24h") or 0
                total_volume = coin.get("total_volume") or 0

                lines.append(f"  {coin['name']} ({symbol}):")
                lines.append(f"    Preço: US$ {price:,.2f}")
                lines.append(f"    Market Cap: US$ {mc:,.0f}")
                lines.append(f"    Volume 24h: US$ {total_volume:,.0f}")
                lines.append(f"    High/Low 24h: US$ {high_24h:,.2f} / US$ {low_24h:,.2f}")
                lines.append(
                    f"    Variação: 24h {change_24h:+.2f}% | "
                    f"7d {change_7d:+.2f}% | 30d {change_30d:+.2f}%"
                )
                lines.append(f"    ATH: US$ {ath:,.2f} (distância do ATH: {ath_change:+.1f}%)")

            logger.info(f"[MarketData] Preços cripto coletados: {len(data)} moedas")
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[MarketData] Falha ao buscar preços cripto: {e}")
            return None

    async def _fetch_global_crypto(self, client: httpx.AsyncClient) -> Optional[str]:
        """Busca dados globais do mercado cripto"""
        try:
            response = await client.get(f"{self.COINGECKO_BASE}/global")
            response.raise_for_status()
            data = response.json()["data"]

            total_mc = data["total_market_cap"]["usd"]
            total_vol = data["total_volume"]["usd"]
            btc_dom = data["market_cap_percentage"]["btc"]
            eth_dom = data["market_cap_percentage"]["eth"]
            mc_change_24h = data.get("market_cap_change_percentage_24h_usd", 0)

            lines = [
                "MERCADO CRIPTO GLOBAL (fonte: CoinGecko):",
                f"  Market Cap Total: US$ {total_mc:,.0f} ({mc_change_24h:+.2f}% 24h)",
                f"  Volume 24h Total: US$ {total_vol:,.0f}",
                f"  Dominância BTC: {btc_dom:.1f}%",
                f"  Dominância ETH: {eth_dom:.1f}%",
            ]

            logger.info("[MarketData] Dados globais cripto coletados")
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[MarketData] Falha ao buscar dados globais: {e}")
            return None

    async def _fetch_fear_greed(self, client: httpx.AsyncClient) -> Optional[str]:
        """Busca Fear & Greed Index"""
        try:
            response = await client.get(
                self.FEAR_GREED_URL,
                params={"limit": 7, "format": "json"},
            )
            response.raise_for_status()
            data = response.json()["data"]

            current = data[0]
            value = current["value"]
            classification = current["value_classification"]

            lines = [
                "FEAR & GREED INDEX CRIPTO (fonte: Alternative.me):",
                f"  Atual: {value}/100 ({classification})",
                "  Últimos 7 dias:",
            ]

            for entry in data[:7]:
                date = datetime.fromtimestamp(int(entry["timestamp"])).strftime("%d/%m")
                lines.append(f"    {date}: {entry['value']} ({entry['value_classification']})")

            logger.info(f"[MarketData] Fear & Greed Index: {value} ({classification})")
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[MarketData] Falha ao buscar Fear & Greed Index: {e}")
            return None

    async def _search_macro_context(self) -> Optional[str]:
        """Busca contexto macroeconômico via web search (DuckDuckGo)"""
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning(
                "[MarketData] ddgs não instalado. "
                "Instale com: pip install ddgs"
            )
            return None

        queries = [
            "Federal Reserve interest rate decision latest",
            "US CPI inflation rate latest data",
            "S&P 500 performance this week",
            "US dollar index DXY this week",
            "Bitcoin spot ETF flows this week",
        ]

        try:
            def _do_search():
                results = []
                with DDGS() as ddgs:
                    for query in queries:
                        try:
                            search_results = list(ddgs.text(query, max_results=2))
                            for r in search_results:
                                results.append(f"  - {r['title']}: {r['body']}")
                        except Exception:
                            continue
                return results

            all_results = await asyncio.to_thread(_do_search)

            if all_results:
                lines = [
                    "CONTEXTO MACROECONÔMICO E NOTÍCIAS RECENTES (fonte: web search):"
                ] + all_results
                logger.info(
                    f"[MarketData] Contexto macro coletado: {len(all_results)} resultados"
                )
                return "\n".join(lines)

            return None

        except Exception as e:
            logger.warning(f"[MarketData] Falha na busca macro: {e}")
            return None


market_data_collector = MarketDataCollector()
