"""
BM25-based keyword search implementation
"""

from typing import List, Dict
from rank_bm25 import BM25Okapi
from loguru import logger
from src.text_processor import TextProcessor


class BM25SearchEngine:
    """
    Sparse retrieval using BM25 algorithm
    """
    
    def __init__(self, documents: List[Dict]):
        """
        Initialize search engine with documents
        
        Args:
            documents: List of document dicts with 'doc_id' and 'text'
        """
        self.documents = documents
        self.processor = TextProcessor()
        
        # Tokenize all documents
        logger.info("Tokenizing documents for BM25...")
        self.tokenized_corpus = [
            self.processor.tokenize(doc['text']) 
            for doc in documents
        ]
        
        # Build BM25 index
        logger.info("Building BM25 index...")
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25 index built for {len(documents)} documents")
        
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search documents using BM25
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of documents with scores, sorted by relevance
        """
        
        # Tokenize query
        query_tokens = self.processor.tokenize(query)
        
        if not query_tokens:
            logger.warning("Query resulted in no tokens after processing")
            return []
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top K document indices
        top_indices = scores.argsort()[-top_k:][::-1]
        
        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include docs with positive scores
                doc = self.documents[idx].copy()
                doc['score'] = float(scores[idx])
                doc['preview'] = self.processor.extract_preview(doc['text'])
                results.append(doc)
        
        logger.info(f"Found {len(results)} results for query: '{query}'")
        return results


# Usage Example
if __name__ == "__main__":
    from src.document_loader import DocumentLoader
    
    # Load documents
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    
    # Create search engine
    search_engine = BM25SearchEngine(documents)
    
    # Search
    results = search_engine.search("Maxwell Paris meeting", top_k=10)
    
    # Display results
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['filename']} (score: {result['score']:.2f})")
        print(f"   {result['preview']}")

