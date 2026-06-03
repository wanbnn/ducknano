# -*- coding: utf-8 -*-
import os
import math
import json
import re
import requests
from collections import defaultdict
from typing import List, Tuple
from ducknano.config import console

def tokenize(text: str) -> List[str]:
    """
    Splits text into tokens, handling normal word boundaries, snake_case, and camelCase.
    """
    raw_words = re.findall(r'[a-zA-Z0-9_]+', text)
    tokens = []
    for word in raw_words:
        if len(word) < 2:
            continue
        # Lowercase the full word
        word_lower = word.lower()
        tokens.append(word_lower)
        
        # Split camelCase / PascalCase
        camel_parts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)', word)
        if len(camel_parts) > 1:
            for part in camel_parts:
                part_lower = part.lower()
                if len(part_lower) >= 2:
                    tokens.append(part_lower)
        
        # Split snake_case
        if '_' in word:
            snake_parts = word.split('_')
            for part in snake_parts:
                part_lower = part.lower()
                if len(part_lower) >= 2:
                    # Also handle camelCase inside snake parts
                    camel_subparts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)', part)
                    if len(camel_subparts) > 1:
                        for subpart in camel_subparts:
                            subpart_lower = subpart.lower()
                            if len(subpart_lower) >= 2:
                                tokens.append(subpart_lower)
                    else:
                        tokens.append(part_lower)
    return tokens


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes cosine similarity between two numeric vectors.
    """
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class LocalTrigramIndex:
    """
    Renamed LocalTrigramIndex to keep backward compatibility.
    Implements:
    - Smart token-based TF-IDF search.
    - Optional embedding search with auto-detection (OAI and native llama.cpp) & local caching.
    - Fallback logic to TF-IDF.
    """
    def __init__(self, target_dir: str, allowed_extensions: List[str] = None):
        self.target_dir = target_dir
        self.allowed_extensions = allowed_extensions
        self.files = []
        self.doc_term_freqs = {}
        self.doc_freqs = defaultdict(int)
        self.idf = {}
        self.doc_norms = {}
        self.embeddings_available = False
        self.embedding_mode = None
        self.native_embedding_url = ""
        self.embeddings_cache = {}
        
        self.rebuild_index()

    def _check_embeddings_available(self) -> bool:
        """
        Probes both OAI and native llama.cpp embedding endpoints.
        Sets self.embedding_mode to 'oai', 'native', or None.
        """
        from ducknano.config import LLAMA_API_URL, EMBEDDINGS_API_URL
        
        # 1. Try OAI endpoint first
        try:
            response = requests.post(
                EMBEDDINGS_API_URL,
                json={"input": "probe", "model": "any"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0 and "embedding" in data["data"][0]:
                    self.embedding_mode = 'oai'
                    return True
        except Exception:
            pass

        # 2. Try native llama.cpp embedding endpoint
        try:
            native_url = LLAMA_API_URL.replace("/v1/chat/completions", "/embedding")
            response = requests.post(
                native_url,
                json={"content": "probe"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0 and "embedding" in data[0]:
                    self.embedding_mode = 'native'
                    self.native_embedding_url = native_url
                    return True
        except Exception:
            pass

        self.embedding_mode = None
        return False

    def _load_embedding_cache(self) -> dict:
        from ducknano.config import EMBEDDING_CACHE_FILE
        if os.path.exists(EMBEDDING_CACHE_FILE):
            try:
                with open(EMBEDDING_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_embedding_cache(self):
        from ducknano.config import EMBEDDING_CACHE_FILE
        try:
            os.makedirs(os.path.dirname(EMBEDDING_CACHE_FILE), exist_ok=True)
            with open(EMBEDDING_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.embeddings_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _fetch_embedding(self, text: str) -> List[float]:
        from ducknano.config import EMBEDDINGS_API_URL
        try:
            if self.embedding_mode == 'oai':
                response = requests.post(
                    EMBEDDINGS_API_URL,
                    json={"input": text, "model": "any"},
                    timeout=60
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and len(data["data"]) > 0 and "embedding" in data["data"][0]:
                        return data["data"][0]["embedding"]
                else:
                    console.print(f"[yellow]RAG: Embedding API returned status {response.status_code}: {response.text}[/yellow]")
            elif self.embedding_mode == 'native':
                response = requests.post(
                    self.native_embedding_url,
                    json={"content": text},
                    timeout=60
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0 and "embedding" in data[0]:
                        return data[0]["embedding"]
                else:
                    console.print(f"[yellow]RAG: Embedding API returned status {response.status_code}: {response.text}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]RAG: Embedding connection error: {e}[/yellow]")
        return []

    def rebuild_index(self):
        self.files.clear()
        self.doc_term_freqs.clear()
        self.doc_freqs.clear()
        self.idf.clear()
        self.doc_norms.clear()
        
        # Check if embeddings endpoint is available
        self.embeddings_available = self._check_embeddings_available()
        if self.embeddings_available:
            self.embeddings_cache = self._load_embedding_cache()
            console.print(f"[dim blue]RAG: Embedding endpoint available and active (mode: {self.embedding_mode}).[/dim blue]")
        else:
            self.embeddings_cache = {}
            console.print("[dim blue]RAG: Embedding endpoint unavailable. Using high-quality TF-IDF search.[/dim blue]")

        if not os.path.exists(self.target_dir):
            return

        ignored_dirs = {
            ".git", "__pycache__", "node_modules", "venv", ".venv",
            ".next", "dist", "build", "out", ".cache", ".yarn", "bower_components"
        }
        ignored_extensions = {
            # Compiled & Binaries
            ".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3", ".class", ".o", ".obj", ".dll", ".so", ".dylib", ".exe",
            # Images & Assets
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
            # Audio & Video
            ".mp3", ".mp4", ".wav", ".avi", ".mkv",
            # Fonts
            ".woff", ".woff2", ".ttf", ".eot",
            # Archives / Bundles
            ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".pack",
            # Rich documents
            ".pdf", ".docx", ".xlsx", ".pptx",
            # Source maps
            ".map"
        }

        # First scan all files and compute their TF
        for root, dirs, filenames in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ignored_extensions:
                    continue
                if self.allowed_extensions and ext not in self.allowed_extensions:
                    continue
                
                full_path = os.path.join(root, filename)
                try:
                    stat = os.stat(full_path)
                    size = stat.st_size
                    mtime = stat.st_mtime
                    if size > 500 * 1024:  # Ignore files > 500KB
                        continue
                except OSError:
                    continue

                filepath = os.path.relpath(full_path, self.target_dir)
                self.files.append(filepath)
                
                # TF-IDF indexing
                self._index_file_tfidf(filepath, full_path)
                
                # Embedding caching
                if self.embeddings_available:
                    self._ensure_embedding_cached(filepath, full_path, mtime, size)

        # Compute IDF
        num_docs = len(self.files)
        if num_docs > 0:
            for term, doc_count in self.doc_freqs.items():
                self.idf[term] = math.log(1.0 + (num_docs / (1.0 + doc_count)))
            
            # Compute document norms
            for filepath in self.files:
                term_freqs = self.doc_term_freqs.get(filepath, {})
                squared_sum = 0.0
                for term, tf in term_freqs.items():
                    w = tf * self.idf[term]
                    squared_sum += w * w
                self.doc_norms[filepath] = math.sqrt(squared_sum)

        # Clean up deleted files from embedding cache and save
        if self.embeddings_available:
            active_files = set(self.files)
            deleted_files = [f for f in self.embeddings_cache if f not in active_files]
            for f in deleted_files:
                del self.embeddings_cache[f]
            self._save_embedding_cache()

    def _index_file_tfidf(self, filepath: str, full_path: str):
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tokens = tokenize(content)
            
            term_counts = defaultdict(int)
            for token in tokens:
                term_counts[token] += 1
            
            self.doc_term_freqs[filepath] = term_counts
            for term in term_counts:
                self.doc_freqs[term] += 1
        except Exception:
            pass

    def _ensure_embedding_cached(self, filepath: str, full_path: str, mtime: float, size: int):
        cached = self.embeddings_cache.get(filepath)
        if cached and cached.get("mtime") == mtime and cached.get("size") == size:
            return

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                # Truncate to 2000 characters (~450 tokens) to safely fit within llama-server's 512 batch limit
                content = f.read(2000)
            emb = self._fetch_embedding(content)
            if emb:
                self.embeddings_cache[filepath] = {
                    "mtime": mtime,
                    "size": size,
                    "embedding": emb
                }
        except Exception:
            pass

    def _search_tfidf(self, query: str, limit: int = 1) -> List[Tuple[str, float]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
            
        query_tf = defaultdict(int)
        for token in query_tokens:
            query_tf[token] += 1
            
        query_weights = {}
        query_norm_sq = 0.0
        for term, tf in query_tf.items():
            idf = self.idf.get(term, 0.0)
            w = tf * idf
            query_weights[term] = w
            query_norm_sq += w * w
            
        query_norm = math.sqrt(query_norm_sq)
        if query_norm == 0.0:
            return []
            
        scores = {}
        for filepath in self.files:
            doc_norm = self.doc_norms.get(filepath, 0.0)
            if doc_norm == 0.0:
                continue
                
            dot_product = 0.0
            doc_tf = self.doc_term_freqs.get(filepath, {})
            for term, qw in query_weights.items():
                if term in doc_tf:
                    dw = doc_tf[term] * self.idf.get(term, 0.0)
                    dot_product += qw * dw
                    
            score = dot_product / (query_norm * doc_norm)
            score = max(0.0, min(1.0, score)) # Clamp to [0.0, 1.0]
            if score > 0.0:
                scores[filepath] = score
                
        if not scores:
            return []
            
        results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return results[:limit]

    def search(self, query: str, limit: int = 1) -> List[Tuple[str, float]]:
        if len(query.strip()) < 3:
            return []
            
        if self.embeddings_available:
            try:
                query_embedding = self._fetch_embedding(query)
                if query_embedding:
                    results = []
                    for filepath in self.files:
                        if filepath in self.embeddings_cache:
                            doc_emb = self.embeddings_cache[filepath].get("embedding")
                            if doc_emb:
                                sim = cosine_similarity(query_embedding, doc_emb)
                                score = max(0.0, min(1.0, sim))
                                results.append((filepath, score))
                    
                    # If embedding search yields valid results, return them
                    if results:
                        results.sort(key=lambda x: x[1], reverse=True)
                        return results[:limit]
            except Exception as e:
                console.print(f"[yellow]RAG: Embedding search failed, fallback to TF-IDF. Error: {e}[/yellow]")
        
        # Fallback to TF-IDF if embeddings are disabled, query failed, or yields no results
        return self._search_tfidf(query, limit)
