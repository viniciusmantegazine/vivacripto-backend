"""
Quality Validation Service
Valida a qualidade do conteúdo gerado
"""
from typing import Dict, List, Tuple
from loguru import logger
import re


class QualityValidator:
    """Validador de qualidade de conteúdo"""
    
    # Palavras-chave obrigatórias (pelo menos uma deve estar presente)
    REQUIRED_KEYWORDS = [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "criptomoeda",
        "blockchain", "defi", "nft", "token", "moeda digital"
    ]
    
    # Limites de qualidade
    MIN_WORD_COUNT = 100
    MAX_WORD_COUNT = 300
    MIN_TITLE_LENGTH = 30
    MAX_TITLE_LENGTH = 100  # Aumentado de 70 para 100
    MIN_EXCERPT_LENGTH = 80
    MAX_EXCERPT_LENGTH = 200  # Aumentado de 150 para 200
    MIN_META_LENGTH = 120
    MAX_META_LENGTH = 180  # Aumentado de 160 para 180
    
    def validate_article(self, article: Dict) -> Tuple[bool, List[str]]:
        """
        Valida a qualidade de um artigo gerado
        
        Args:
            article: Artigo a ser validado
            
        Returns:
            Tupla (is_valid, errors) onde is_valid é bool e errors é lista de erros
        """
        errors = []
        
        # 1. Validar contagem de palavras
        word_count_valid, word_count_error = self._validate_word_count(article)
        if not word_count_valid:
            errors.append(word_count_error)
        
        # 2. Validar presença de keywords
        keywords_valid, keywords_error = self._validate_keywords(article)
        if not keywords_valid:
            errors.append(keywords_error)
        
        # 3. Validar título
        title_valid, title_error = self._validate_title(article)
        if not title_valid:
            errors.append(title_error)
        
        # 4. Validar excerpt
        excerpt_valid, excerpt_error = self._validate_excerpt(article)
        if not excerpt_valid:
            errors.append(excerpt_error)
        
        # 5. Validar meta description
        meta_valid, meta_error = self._validate_meta_description(article)
        if not meta_valid:
            errors.append(meta_error)
        
        # 6. Validar estrutura do conteúdo
        structure_valid, structure_error = self._validate_content_structure(article)
        if not structure_valid:
            errors.append(structure_error)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"Artigo validado com sucesso: {article.get('title', '')[:50]}")
        else:
            logger.warning(f"Artigo reprovado na validação: {', '.join(errors)}")
        
        return is_valid, errors
    
    def _validate_word_count(self, article: Dict) -> Tuple[bool, str]:
        """Valida a contagem de palavras do conteúdo"""
        content = article.get("content_markdown", "")
        word_count = len(content.split())
        
        if word_count < self.MIN_WORD_COUNT:
            return False, f"Conteúdo muito curto ({word_count} palavras, mínimo {self.MIN_WORD_COUNT})"
        
        if word_count > self.MAX_WORD_COUNT:
            return False, f"Conteúdo muito longo ({word_count} palavras, máximo {self.MAX_WORD_COUNT})"
        
        return True, ""
    
    def _validate_keywords(self, article: Dict) -> Tuple[bool, str]:
        """Valida a presença de palavras-chave relevantes"""
        content = article.get("content_markdown", "").lower()
        title = article.get("title", "").lower()
        text = f"{title} {content}"
        
        has_keyword = any(keyword in text for keyword in self.REQUIRED_KEYWORDS)
        
        if not has_keyword:
            return False, "Nenhuma palavra-chave relevante encontrada"
        
        return True, ""
    
    def _validate_title(self, article: Dict) -> Tuple[bool, str]:
        """Valida o título do artigo (com truncamento automático)"""
        title = article.get("title", "")
        
        if not title:
            return False, "Título ausente"
        
        title_length = len(title)
        
        if title_length < self.MIN_TITLE_LENGTH:
            return False, f"Título muito curto ({title_length} caracteres, mínimo {self.MIN_TITLE_LENGTH})"
        
        # Truncar automaticamente se muito longo
        if title_length > self.MAX_TITLE_LENGTH:
            article["title"] = title[:self.MAX_TITLE_LENGTH].rsplit(' ', 1)[0] + "..."
            logger.info(f"Título truncado de {title_length} para {len(article['title'])} caracteres")
        
        return True, ""
    
    def _validate_excerpt(self, article: Dict) -> Tuple[bool, str]:
        """Valida o excerpt do artigo (com truncamento automático)"""
        excerpt = article.get("excerpt", "")
        
        if not excerpt:
            return False, "Excerpt ausente"
        
        excerpt_length = len(excerpt)
        
        if excerpt_length < self.MIN_EXCERPT_LENGTH:
            return False, f"Excerpt muito curto ({excerpt_length} caracteres)"
        
        # Truncar automaticamente se muito longo
        if excerpt_length > self.MAX_EXCERPT_LENGTH:
            article["excerpt"] = excerpt[:self.MAX_EXCERPT_LENGTH].rsplit(' ', 1)[0] + "..."
            logger.info(f"Excerpt truncado de {excerpt_length} para {len(article['excerpt'])} caracteres")
        
        return True, ""
    
    def _validate_meta_description(self, article: Dict) -> Tuple[bool, str]:
        """Valida a meta description (com truncamento automático)"""
        meta_desc = article.get("meta_description", "")
        
        if not meta_desc:
            return False, "Meta description ausente"
        
        meta_length = len(meta_desc)
        
        if meta_length < self.MIN_META_LENGTH:
            return False, f"Meta description muito curta ({meta_length} caracteres)"
        
        # Truncar automaticamente se muito longa
        if meta_length > self.MAX_META_LENGTH:
            article["meta_description"] = meta_desc[:self.MAX_META_LENGTH].rsplit(' ', 1)[0] + "..."
            logger.info(f"Meta description truncada de {meta_length} para {len(article['meta_description'])} caracteres")
        
        return True, ""
    
    def _validate_content_structure(self, article: Dict) -> Tuple[bool, str]:
        """Valida a estrutura do conteúdo (parágrafos, formatação)"""
        content = article.get("content_markdown", "")
        
        # Verificar se tem pelo menos 2 parágrafos
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 2:
            return False, "Conteúdo deve ter pelo menos 2 parágrafos"
        
        # Verificar se não é apenas uma lista
        if content.strip().startswith('-') or content.strip().startswith('*'):
            lines = content.strip().split('\n')
            list_lines = [l for l in lines if l.strip().startswith(('-', '*'))]
            if len(list_lines) / len(lines) > 0.7:
                return False, "Conteúdo não pode ser majoritariamente listas"
        
        return True, ""
