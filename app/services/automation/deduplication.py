"""
Deduplication and Filtering Service
Remove notícias duplicadas e filtra conteúdo relevante
"""
from typing import List, Dict, Set
from datetime import datetime, timedelta
from loguru import logger
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.db.base import get_async_session
from app.crud.crud_post import crud_post
from sqlalchemy.ext.asyncio import AsyncSession


class DeduplicationService:
    """Serviço de deduplicação e filtragem de notícias"""
    
    def __init__(self):
        # Modelo para embeddings semânticos
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.similarity_threshold = 0.75  # 75% de similaridade = duplicado
    
    async def filter_and_deduplicate(
        self, 
        news_items: List[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """
        Filtra e remove duplicatas das notícias coletadas
        
        Args:
            news_items: Lista de notícias coletadas
            db: Sessão do banco de dados
            
        Returns:
            Lista de notícias únicas e relevantes
        """
        logger.info(f"Iniciando filtragem e deduplicação de {len(news_items)} notícias")
        
        # 1. Remover duplicatas por URL
        news_items = self._remove_url_duplicates(news_items)
        logger.info(f"Após remoção por URL: {len(news_items)} notícias")
        
        # 2. Filtrar por palavras-chave relevantes
        news_items = self._filter_by_keywords(news_items)
        logger.info(f"Após filtro de keywords: {len(news_items)} notícias")
        
        # 3. Remover duplicatas semânticas (similaridade de cosseno)
        news_items = await self._remove_semantic_duplicates(news_items)
        logger.info(f"Após deduplicação semântica: {len(news_items)} notícias")
        
        # 4. Comparar com posts existentes no banco (últimos 7 dias)
        news_items = await self._filter_existing_posts(news_items, db)
        logger.info(f"Após comparação com banco: {len(news_items)} notícias únicas")
        
        return news_items
    
    def _remove_url_duplicates(self, news_items: List[Dict]) -> List[Dict]:
        """Remove notícias com URLs duplicadas"""
        seen_urls: Set[str] = set()
        unique_items = []
        
        for item in news_items:
            url = item.get("url", "").strip().lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
        
        return unique_items
    
    def _filter_by_keywords(self, news_items: List[Dict]) -> List[Dict]:
        """Filtra notícias por palavras-chave relevantes"""
        # Keywords relevantes para criptomoedas
        relevant_keywords = {
            "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
            "blockchain", "defi", "nft", "altcoin", "trading", "exchange",
            "wallet", "mining", "staking", "token", "coin", "web3",
            "binance", "coinbase", "solana", "cardano", "polygon", "avalanche"
        }
        
        # Keywords para excluir (spam, clickbait)
        exclude_keywords = {
            "sponsored", "advertisement", "promo", "giveaway", "airdrop scam"
        }
        
        filtered_items = []
        
        for item in news_items:
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()
            text = f"{title} {description}"
            
            # Verificar se contém keywords relevantes
            has_relevant = any(keyword in text for keyword in relevant_keywords)
            
            # Verificar se contém keywords de exclusão
            has_exclude = any(keyword in text for keyword in exclude_keywords)
            
            if has_relevant and not has_exclude:
                filtered_items.append(item)
        
        return filtered_items
    
    async def _remove_semantic_duplicates(self, news_items: List[Dict]) -> List[Dict]:
        """Remove duplicatas usando similaridade de cosseno"""
        if len(news_items) <= 1:
            return news_items
        
        # Extrair títulos
        titles = [item.get("title", "") for item in news_items]
        
        # Gerar embeddings
        embeddings = self.model.encode(titles)
        
        # Calcular matriz de similaridade
        similarity_matrix = cosine_similarity(embeddings)
        
        # Marcar duplicatas
        to_keep = []
        seen_indices = set()
        
        for i in range(len(news_items)):
            if i in seen_indices:
                continue
            
            to_keep.append(i)
            
            # Marcar itens similares como vistos
            for j in range(i + 1, len(news_items)):
                if similarity_matrix[i][j] >= self.similarity_threshold:
                    seen_indices.add(j)
        
        unique_items = [news_items[i] for i in to_keep]
        
        return unique_items
    
    async def _filter_existing_posts(
        self, 
        news_items: List[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Filtra notícias que já existem no banco (últimos 7 dias)"""
        # Buscar posts dos últimos 7 dias
        cutoff_date = datetime.now() - timedelta(days=7)
        existing_posts = await crud_post.get_recent_posts(db, since=cutoff_date)
        
        if not existing_posts:
            return news_items
        
        # Extrair títulos dos posts existentes
        existing_titles = [post.title for post in existing_posts]
        
        # Gerar embeddings
        existing_embeddings = self.model.encode(existing_titles)
        new_titles = [item.get("title", "") for item in news_items]
        new_embeddings = self.model.encode(new_titles)
        
        # Calcular similaridade
        similarity_matrix = cosine_similarity(new_embeddings, existing_embeddings)
        
        # Filtrar notícias não similares
        unique_items = []
        for i, item in enumerate(news_items):
            max_similarity = np.max(similarity_matrix[i])
            if max_similarity < self.similarity_threshold:
                unique_items.append(item)
        
        return unique_items
