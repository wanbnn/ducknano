# -*- coding: utf-8 -*-
import os
from collections import defaultdict
from typing import List, Tuple

class LocalTrigramIndex:
    def __init__(self, target_dir: str, allowed_extensions: List[str] = None):
        self.target_dir = target_dir
        self.allowed_extensions = allowed_extensions
        self.index = defaultdict(set)
        self.files = []
        self.rebuild_index()

    def rebuild_index(self):
        self.index.clear()
        self.files.clear()
        if not os.path.exists(self.target_dir):
            return

        ignored_dirs = {".git", "__pycache__", "node_modules", "venv", ".venv"}
        for root, dirs, filenames in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if self.allowed_extensions and ext not in self.allowed_extensions:
                    continue
                
                filepath = os.path.relpath(os.path.join(root, filename), self.target_dir)
                self.files.append(filepath)
                self._index_file(filepath)

    def _index_file(self, filepath: str):
        full_path = os.path.join(self.target_dir, filepath)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                for i in range(len(content) - 2):
                    trigram = content[i:i+3]
                    self.index[trigram].add(filepath)
        except Exception:
            pass

    def search(self, query: str, limit: int = 1) -> List[Tuple[str, float]]:
        query = query.lower()
        if len(query) < 3:
            return []
            
        scores = defaultdict(int)
        query_trigrams = set()
        
        for i in range(len(query) - 2):
            trigram = query[i:i+3]
            query_trigrams.add(trigram)
            if trigram in self.index:
                for filepath in self.index[trigram]:
                    scores[filepath] += 1
        
        if not scores:
            return []

        results = []
        for filepath, match_count in scores.items():
            normalized_score = match_count / len(query_trigrams)
            results.append((filepath, normalized_score))
            
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
