# -*- coding: utf-8 -*-
import os
import time
from typing import List, Dict
from ducknano.config import MEMORY_DIR, console
from ducknano.rag import LocalTrigramIndex

class MemoryManager:
    def __init__(self):
        self.index_engine = LocalTrigramIndex(MEMORY_DIR, allowed_extensions=[".txt"])

    def archive_interaction_chunk(self, messages_to_archive: List[Dict[str, str]]):
        if not messages_to_archive:
            return
            
        timestamp = int(time.time() * 1000)
        chunk_filename = f"mem_chunk_{timestamp}.txt"
        chunk_path = os.path.join(MEMORY_DIR, chunk_filename)
        
        formatted_content = []
        for msg in messages_to_archive:
            if msg["role"] in ("user", "assistant"):
                formatted_content.append(f"[{msg['role'].upper()}]: {msg['content']}")
                
        if formatted_content:
            try:
                with open(chunk_path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(formatted_content))
                self.index_engine.rebuild_index()
                console.print(f"[dim blue]RAG: Memory chunk saved - {chunk_filename}[/dim blue]")
            except Exception as e:
                console.print(f"[red]Erro memory fragment: {e}[/red]")

    def retrieve_relevant_memory(self, query: str) -> str:
        matches = self.index_engine.search(query, limit=1)
        if not matches:
            return ""
            
        best_match_file, score = matches[0]
        if score < 0.15:
            return ""
            
        full_path = os.path.join(MEMORY_DIR, best_match_file)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            console.print(f"[bold cyan]🔍 RAG: Memory of '{best_match_file}' (Score: {score:.2f})[/bold cyan]")
            return content
        except Exception:
            return ""
