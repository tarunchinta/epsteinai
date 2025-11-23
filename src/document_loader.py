"""
Load and validate .txt files from directory
"""

from pathlib import Path
from typing import List, Dict
import chardet
from loguru import logger


class DocumentLoader:
    """Load text documents from filesystem"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        
    def load_documents(self) -> List[Dict]:
        """
        Load all .txt files from directory
        
        Returns:
            List of document dictionaries with structure:
            {
                'doc_id': str,
                'filename': str,
                'text': str,
                'metadata': {
                    'size': int,
                    'encoding': str
                }
            }
        """
        documents = []
        txt_files = list(self.data_dir.glob("**/*.txt"))
        
        logger.info(f"Found {len(txt_files)} text files")
        
        for idx, filepath in enumerate(txt_files):
            try:
                doc = self._load_single_file(filepath, idx)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
                
        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents
    
    def _load_single_file(self, filepath: Path, doc_id: int) -> Dict:
        """Load a single text file with encoding detection"""
        
        # Detect encoding
        with open(filepath, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding'] or 'utf-8'
        
        # Read with detected encoding
        try:
            text = raw_data.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            text = raw_data.decode('utf-8', errors='ignore')
            logger.warning(f"Encoding issue in {filepath}, used fallback")
        
        return {
            'doc_id': f"doc_{doc_id:06d}",
            'filename': filepath.name,
            'filepath': str(filepath),
            'text': text,
            'metadata': {
                'size': len(text),
                'encoding': encoding,
                'file_size_bytes': filepath.stat().st_size
            }
        }


# Usage Example
if __name__ == "__main__":
    loader = DocumentLoader("data")
    documents = loader.load_documents()
    print(f"Loaded {len(documents)} documents")
    if documents:
        print(f"First doc: {documents[0]['filename']}")
        print(f"First 100 chars: {documents[0]['text'][:100]}")

