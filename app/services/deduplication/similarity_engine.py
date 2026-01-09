"""
Módulo de Similaridade Semântica para Detecção de Duplicatas
Implementa múltiplas estratégias de comparação de textos
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import math
from collections import Counter
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimilarityResult:
    """Resultado da análise de similaridade"""
    score: float  # 0.0 a 1.0
    method: str
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SimilarityEngine(ABC):
    """Interface base para motores de similaridade"""
    
    @abstractmethod
    def calculate(self, text1: str, text2: str) -> SimilarityResult:
        """Calcula similaridade entre dois textos"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome do motor"""
        pass


class LevenshteinSimilarity(SimilarityEngine):
    """
    Implementa Distância de Levenshtein normalizada
    Simples e rápido, ideal para detecção de duplicatas exatas/próximas
    """
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calcula a distância de Levenshtein entre duas strings"""
        if len(s1) < len(s2):
            return LevenshteinSimilarity.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Custo de inserção, deleção ou substituição
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def calculate(self, text1: str, text2: str) -> SimilarityResult:
        """Calcula similaridade usando Levenshtein"""
        # Normalizar textos
        text1_clean = text1.lower().strip()
        text2_clean = text2.lower().strip()
        
        # Calcular distância
        distance = self.levenshtein_distance(text1_clean, text2_clean)
        max_length = max(len(text1_clean), len(text2_clean))
        
        # Converter para similaridade (0-1)
        if max_length == 0:
            similarity = 1.0
        else:
            similarity = 1.0 - (distance / max_length)
        
        return SimilarityResult(
            score=similarity,
            method="levenshtein",
            details={
                "distance": distance,
                "max_length": max_length
            }
        )
    
    def get_name(self) -> str:
        return "Levenshtein"


class TFIDFSimilarity(SimilarityEngine):
    """
    Implementa similaridade baseada em TF-IDF com Cosine Similarity
    Melhor para detectar similaridade semântica em conteúdo mais longo
    """
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokeniza o texto em palavras"""
        import re
        # Remover pontuação e converter para minúsculas
        text = text.lower()
        # Remover caracteres especiais, mantendo apenas letras, números e espaços
        text = re.sub(r'[^a-záéíóúâêôãõç\s0-9]', '', text)
        # Dividir em palavras
        words = text.split()
        # Remover stopwords comuns
        stopwords = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
            'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas',
            'e', 'ou', 'para', 'por', 'com', 'sem', 'sob', 'sobre',
            'é', 'são', 'foi', 'foram', 'ser', 'estar',
            'que', 'qual', 'quais', 'quanto', 'quantos',
            'este', 'esse', 'aquele', 'isto', 'isso', 'aquilo',
            'eu', 'tu', 'ele', 'ela', 'nós', 'vós', 'eles', 'elas',
            'meu', 'teu', 'seu', 'nosso', 'vosso',
            'já', 'ainda', 'também', 'nem', 'só', 'somente'
        }
        return [w for w in words if w and w not in stopwords]
    
    @staticmethod
    def calculate_tf(tokens: List[str]) -> Dict[str, float]:
        """Calcula Term Frequency"""
        counter = Counter(tokens)
        total = len(tokens)
        return {word: count / total for word, count in counter.items()}
    
    @staticmethod
    def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calcula similaridade do cosseno entre dois vetores"""
        # Palavras em comum
        common_words = set(vec1.keys()) & set(vec2.keys())
        
        if not common_words:
            return 0.0
        
        # Produto escalar
        dot_product = sum(vec1[word] * vec2[word] for word in common_words)
        
        # Magnitude dos vetores
        mag1 = math.sqrt(sum(val ** 2 for val in vec1.values()))
        mag2 = math.sqrt(sum(val ** 2 for val in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def calculate(self, text1: str, text2: str) -> SimilarityResult:
        """Calcula similaridade usando TF-IDF + Cosine"""
        tokens1 = self.tokenize(text1)
        tokens2 = self.tokenize(text2)
        
        if not tokens1 or not tokens2:
            return SimilarityResult(
                score=1.0 if text1.strip() == text2.strip() else 0.0,
                method="tfidf",
                details={"tokens1": len(tokens1), "tokens2": len(tokens2)}
            )
        
        tf1 = self.calculate_tf(tokens1)
        tf2 = self.calculate_tf(tokens2)
        
        similarity = self.cosine_similarity(tf1, tf2)
        
        return SimilarityResult(
            score=similarity,
            method="tfidf",
            details={
                "tokens1": len(tokens1),
                "tokens2": len(tokens2),
                "common_tokens": len(set(tokens1) & set(tokens2))
            }
        )
    
    def get_name(self) -> str:
        return "TF-IDF"


class EmbeddingSimilarity(SimilarityEngine):
    """
    Implementa similaridade usando Embeddings (Sentence-Transformers)
    Melhor para compreensão semântica profunda
    Requer: pip install sentence-transformers
    """
    
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        """
        Inicializa o motor de embeddings
        
        Args:
            model_name: Nome do modelo Sentence-Transformers
                       (suporta português e múltiplos idiomas)
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info(f"Modelo de embeddings carregado: {model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers não instalado. "
                "Instale com: pip install sentence-transformers"
            )
            self.model = None
    
    def calculate(self, text1: str, text2: str) -> SimilarityResult:
        """Calcula similaridade usando embeddings"""
        if self.model is None:
            logger.error("Modelo de embeddings não disponível")
            raise RuntimeError(
                "Modelo de embeddings não inicializado. "
                "Instale sentence-transformers."
            )
        
        # Gerar embeddings
        embeddings1 = self.model.encode(text1, convert_to_tensor=False)
        embeddings2 = self.model.encode(text2, convert_to_tensor=False)
        
        # Calcular similaridade do cosseno
        similarity = self._cosine_similarity_vectors(embeddings1, embeddings2)
        
        return SimilarityResult(
            score=similarity,
            method="embedding",
            details={
                "model": self.model_name,
                "embedding_dim": len(embeddings1)
            }
        )
    
    @staticmethod
    def _cosine_similarity_vectors(vec1: List[float], vec2: List[float]) -> float:
        """Calcula similaridade do cosseno entre dois vetores"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a ** 2 for a in vec1))
        mag2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def get_name(self) -> str:
        return "Embedding"


class HybridSimilarity(SimilarityEngine):
    """
    Combina múltiplas estratégias de similaridade
    Usa média ponderada dos scores
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Inicializa o motor híbrido
        
        Args:
            weights: Dicionário com pesos para cada método
                    Ex: {"levenshtein": 0.2, "tfidf": 0.3, "embedding": 0.5}
        """
        self.engines = {
            "levenshtein": LevenshteinSimilarity(),
            "tfidf": TFIDFSimilarity(),
        }
        
        # Tentar adicionar embedding se disponível
        try:
            self.engines["embedding"] = EmbeddingSimilarity()
        except Exception as e:
            logger.warning(f"Embedding não disponível: {e}")
        
        # Pesos padrão
        if weights is None:
            if len(self.engines) == 3:
                weights = {
                    "levenshtein": 0.2,
                    "tfidf": 0.3,
                    "embedding": 0.5
                }
            elif len(self.engines) == 2:
                weights = {
                    "levenshtein": 0.3,
                    "tfidf": 0.7
                }
            else:
                weights = {"levenshtein": 1.0}
        
        self.weights = weights
        logger.info(f"Motor híbrido inicializado com pesos: {self.weights}")
    
    def calculate(self, text1: str, text2: str) -> SimilarityResult:
        """Calcula similaridade usando múltiplos motores"""
        scores = {}
        details = {}
        
        for method, engine in self.engines.items():
            try:
                result = engine.calculate(text1, text2)
                scores[method] = result.score
                details[method] = result.details
            except Exception as e:
                logger.warning(f"Erro ao calcular {method}: {e}")
                scores[method] = 0.0
        
        # Calcular média ponderada
        total_weight = sum(self.weights.get(m, 0) for m in scores.keys())
        if total_weight == 0:
            weighted_score = 0.0
        else:
            weighted_score = sum(
                scores[m] * self.weights.get(m, 0)
                for m in scores.keys()
            ) / total_weight
        
        return SimilarityResult(
            score=weighted_score,
            method="hybrid",
            details={
                "individual_scores": scores,
                "weights": self.weights,
                "engine_details": details
            }
        )
    
    def get_name(self) -> str:
        return "Hybrid"


class SimilarityFactory:
    """Factory para criar instâncias de motores de similaridade"""
    
    @staticmethod
    def create(engine_type: str = "hybrid") -> SimilarityEngine:
        """
        Cria uma instância do motor de similaridade
        
        Args:
            engine_type: "levenshtein", "tfidf", "embedding", ou "hybrid"
        
        Returns:
            Instância do motor de similaridade
        """
        engines = {
            "levenshtein": LevenshteinSimilarity,
            "tfidf": TFIDFSimilarity,
            "embedding": EmbeddingSimilarity,
            "hybrid": HybridSimilarity
        }
        
        if engine_type not in engines:
            logger.warning(
                f"Motor {engine_type} não encontrado. Usando hybrid."
            )
            engine_type = "hybrid"
        
        engine_class = engines[engine_type]
        return engine_class()


# Exemplo de uso
if __name__ == "__main__":
    # Textos de teste
    text1 = "Bank of America e Coinbase anunciam parceria estratégica para criptomoedas"
    text2 = "Coinbase e Bank of America firmam acordo sobre moedas digitais"
    text3 = "Bitcoin atinge novo recorde histórico acima de 100 mil dólares"
    
    # Testar diferentes motores
    print("=" * 70)
    print("TESTE DE SIMILARIDADE")
    print("=" * 70)
    
    print(f"\nTexto 1: {text1}")
    print(f"Texto 2: {text2}")
    print(f"Texto 3: {text3}")
    
    # Levenshtein
    print("\n--- Levenshtein ---")
    lev = SimilarityFactory.create("levenshtein")
    result = lev.calculate(text1, text2)
    print(f"Similaridade (1 vs 2): {result.score:.2%}")
    result = lev.calculate(text1, text3)
    print(f"Similaridade (1 vs 3): {result.score:.2%}")
    
    # TF-IDF
    print("\n--- TF-IDF ---")
    tfidf = SimilarityFactory.create("tfidf")
    result = tfidf.calculate(text1, text2)
    print(f"Similaridade (1 vs 2): {result.score:.2%}")
    result = tfidf.calculate(text1, text3)
    print(f"Similaridade (1 vs 3): {result.score:.2%}")
    
    # Hybrid
    print("\n--- Hybrid ---")
    hybrid = SimilarityFactory.create("hybrid")
    result = hybrid.calculate(text1, text2)
    print(f"Similaridade (1 vs 2): {result.score:.2%}")
    print(f"Detalhes: {result.details}")
    result = hybrid.calculate(text1, text3)
    print(f"Similaridade (1 vs 3): {result.score:.2%}")
