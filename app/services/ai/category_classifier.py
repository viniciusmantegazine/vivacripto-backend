"""
Automatic category classification for crypto news
"""
from typing import Optional
from app.core.logging import logger


class CategoryClassifier:
    """
    Classifies crypto news articles into predefined categories
    based on content analysis and keyword matching
    """
    
    # Category keywords mapping
    CATEGORY_KEYWORDS = {
        'bitcoin': [
            'bitcoin', 'btc', 'satoshi', 'halving', 'lightning network',
            'taproot', 'segwit', 'block reward', 'mining bitcoin'
        ],
        'ethereum': [
            'ethereum', 'eth', 'ether', 'vitalik', 'eip', 'merge', 'pos',
            'proof of stake', 'smart contract', 'solidity', 'gas fee',
            'layer 2', 'rollup', 'optimism', 'arbitrum'
        ],
        'altcoins': [
            'altcoin', 'solana', 'cardano', 'polkadot', 'avalanche',
            'polygon', 'chainlink', 'ripple', 'xrp', 'litecoin', 'ltc',
            'dogecoin', 'doge', 'shiba', 'ada', 'sol', 'dot', 'matic',
            'bnb', 'binance coin', 'tron', 'trx'
        ],
        'defi': [
            'defi', 'decentralized finance', 'yield farming', 'liquidity',
            'amm', 'automated market maker', 'lending', 'borrowing',
            'staking', 'liquidity pool', 'uniswap', 'aave', 'compound',
            'makerdao', 'dai', 'stablecoin', 'usdc', 'usdt', 'tether',
            'swap', 'dex', 'decentralized exchange'
        ],
        'regulacao': [
            'regulation', 'regulação', 'regulamentação', 'sec', 'cftc',
            'governo', 'government', 'lei', 'law', 'compliance', 'kyc',
            'aml', 'tax', 'imposto', 'legal', 'tribunal', 'court',
            'ban', 'proibição', 'autorização', 'approval', 'etf',
            'securities', 'commodity'
        ],
        'airdrop': [
            'airdrop', 'token distribution', 'free tokens', 'claim',
            'snapshot', 'eligibility', 'distribuição gratuita',
            'tokens grátis', 'recompensa', 'reward', 'giveaway',
            'incentivo', 'testnet reward'
        ]
    }
    
    def classify(self, title: str, content: str, excerpt: str) -> Optional[str]:
        """
        Classify article into a category based on content analysis
        
        Args:
            title: Article title
            content: Article content (markdown)
            excerpt: Article excerpt
            
        Returns:
            Category slug or None if no match
        """
        # Combine all text for analysis
        full_text = f"{title} {excerpt} {content}".lower()
        
        # Count keyword matches for each category
        category_scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                # Count occurrences of each keyword
                count = full_text.count(keyword.lower())
                if count > 0:
                    score += count
                    matched_keywords.append(keyword)
            
            if score > 0:
                category_scores[category] = {
                    'score': score,
                    'keywords': matched_keywords
                }
        
        # If no matches, default to 'altcoins' (most generic)
        if not category_scores:
            logger.info(f"No category match found, defaulting to 'altcoins' for: {title[:50]}...")
            return 'altcoins'
        
        # Get category with highest score
        best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
        category_slug = best_category[0]
        score_data = best_category[1]
        
        logger.info(
            f"Classified as '{category_slug}' (score: {score_data['score']}) "
            f"for: {title[:50]}... "
            f"Keywords: {', '.join(score_data['keywords'][:5])}"
        )
        
        return category_slug
    
    def get_category_name(self, slug: str) -> str:
        """Get display name for category slug"""
        category_names = {
            'bitcoin': 'Bitcoin',
            'ethereum': 'Ethereum',
            'altcoins': 'Altcoins',
            'defi': 'DeFi',
            'regulacao': 'Regulação',
            'airdrop': 'Airdrop'
        }
        return category_names.get(slug, 'Altcoins')


# Singleton instance
category_classifier = CategoryClassifier()
