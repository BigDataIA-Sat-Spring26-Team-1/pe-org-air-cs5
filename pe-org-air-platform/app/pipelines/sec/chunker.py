from typing import List
import structlog

logger = structlog.get_logger()

class SemanticChunker:
    """
    Splits text into chunks preserving semantic boundaries (sentences, paragraphs).
    """
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Delimiters in order of priority to split by
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def chunk(self, text: str) -> List[str]:
        """
        Recursively splits text into chunks.
        """
        final_chunks = []
        if not text:
            return []
            
        self._split_recursive(text, self.separators, final_chunks)
        return final_chunks

    def _split_recursive(self, text: str, separators: List[str], final_chunks: List[str]):
        """
        Recursive helper.
        """
        # If text matches size constraints, keep it.
        if len(text) <= self.chunk_size:
            final_chunks.append(text)
            return

        # If no separators left, force split (unlikely with " " and "")
        if not separators:
            # Hard cutoff
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                final_chunks.append(text[i:i + self.chunk_size])
            return

        # Pop separator
        separator = separators[0]
        new_separators = separators[1:]
        
        # Split
        if separator == "":
             splits = list(text) # Character split
        else:
             splits = text.split(separator)
             
        # Re-merge small splits to build up to chunk_size
        current_doc = []
        current_len = 0
        
        for split in splits:
            ws = separator if separator else ""
            len_split = len(split) + len(ws)
            
            if current_len + len_split > self.chunk_size:
                # Flush
                if current_doc:
                    doc = ws.join(current_doc)
                    # Recurse on this doc if it's still too big (unlikely unless single split gigantic)
                    if len(doc) > self.chunk_size:
                        self._split_recursive(doc, new_separators, final_chunks)
                    else:
                        final_chunks.append(doc)
                    
                    # Overlap handling (simplified: minimal overlap from previous)
                    # For strict overlap, logic is more complex.
                    # Here we just reset.
                    current_doc = []
                    current_len = 0
            
            current_doc.append(split)
            current_len += len_split
            
        # Flush remainder
        if current_doc:
            doc = ws.join(current_doc)
            final_chunks.append(doc)

