# -*- coding: utf-8 -*-
import os
import re
import subprocess
from typing import List
from ducknano.config import WORKSPACE_DIR, console

def read_file(path: str, start_line: int = 1, end_line: int = 100) -> str:
    """
    Le um arquivo de forma segura limitando o retorno a no maximo 100 linhas por chamada.
    """
    full_path = os.path.join(WORKSPACE_DIR, path)
    if not os.path.exists(full_path):
        return f"Error: File {path} does not exist."
        
    if start_line < 1:
        start_line = 1
        
    # Restricao de no maximo 100 linhas
    if (end_line - start_line) >= 100:
        end_line = start_line + 99
        
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line)
        
        sliced_lines = lines[start_idx:end_idx]
        
        output = [f"Lines {start_line} to {end_idx} of {total_lines} in {path}:"]
        for idx, line in enumerate(sliced_lines, start=start_line):
            output.append(f"{idx:03d}: {line.rstrip('\r\n')}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error reading file {path}: {e}"

def execute_bash(cmd: str) -> str:
    import platform
    console.print(f"[bold blue]Executando comando:[/bold blue] {cmd}")
    try:
        if platform.system() == "Windows":
            # Use PowerShell on Windows for unix-compatible commands (mkdir -p, ls, cat, etc.)
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                text=True, capture_output=True, timeout=30
            )
        else:
            result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=30)
        stdout = result.stdout[:2000]
        stderr = result.stderr[:2000]
        
        output = ""
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
            output += f"STDERR:\n{stderr}\n"
        if not output:
            output = "Command executed successfully."
        return output
    except subprocess.TimeoutExpired:
        return "Error: The command reached the execution timeout limit (30s)."
    except Exception as e:
        return f"Error executing command: {e}"

def write_file(path: str, content: str) -> str:
    full_path = os.path.join(WORKSPACE_DIR, path)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created/updated successfully: {path}"
    except Exception as e:
        return f"Error writing to file {path}: {e}"

def edit_file(path: str, search_block: str, replace_block: str) -> str:
    full_path = os.path.join(WORKSPACE_DIR, path)
    if not os.path.exists(full_path):
        return f"Error: File {path} does not exist for editing."
        
    if not search_block.strip():
        return "Error: The search block (SEARCH) cannot be empty."
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        search_clean = search_block.strip()
        replace_clean = replace_block.strip()
        
        if search_clean not in content:
            if search_clean.strip() in content.strip():
                content = content.replace(search_clean.strip(), replace_clean)
            else:
                return f"Error: Could not locate the exact SEARCH block in {path}."
        else:
            content = content.replace(search_block, replace_block)
            
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"File {path} edited successfully."
    except Exception as e:
        return f"Error editing file {path}: {e}"

def preprocess_response(response: str) -> str:
    pattern = re.compile(r'\[CMD:(read_file|write_file|edit_file|run_bash|recall_memory|search_workspace)(?:\s+[^\]]*)?\]')
    matches = list(pattern.finditer(response))
    if not matches:
        return response

    parts = []
    last_idx = 0
    for i in range(len(matches)):
        match = matches[i]
        start_idx = match.start()
        end_idx = match.end()
        next_start_idx = matches[i+1].start() if i+1 < len(matches) else len(response)
        
        content_span = response[end_idx:next_start_idx]
        
        if '[/CMD]' not in content_span:
            if content_span.endswith('\n'):
                corrected_content = content_span + '[/CMD]\n'
            else:
                corrected_content = content_span + '\n[/CMD]\n'
        else:
            corrected_content = content_span

        parts.append(response[last_idx:end_idx])
        parts.append(corrected_content)
        last_idx = next_start_idx

    if last_idx < len(response):
        parts.append(response[last_idx:])
        
    return "".join(parts)

def parse_and_execute_commands(response: str, workspace_index=None, memory_manager=None) -> List[str]:
    response = preprocess_response(response)
    results = []

    # 1. Regex para [CMD:read_file ...]
    read_pattern = re.compile(
        r'\[CMD:read_file\s+path="([^"]+)"(?:\s+start_line=(\d+))?(?:\s+end_line=(\d+))?\](.*?)\[/CMD\]',
        re.DOTALL
    )
    for match in read_pattern.finditer(response):
        filepath = match.group(1)
        start_l = int(match.group(2)) if match.group(2) else 1
        end_l = int(match.group(3)) if match.group(3) else 100
        res = read_file(filepath, start_l, end_l)
        results.append(res)

    # 2. Regex para [CMD:write_file ...]
    write_pattern = re.compile(r'\[CMD:write_file\s+path="([^"]+)"\](.*?)\[/CMD\]', re.DOTALL)
    for match in write_pattern.finditer(response):
        filepath = match.group(1)
        content = match.group(2).strip("\r\n")
        res = write_file(filepath, content)
        if workspace_index:
            workspace_index.rebuild_index()
        results.append(res)

    # 3. Regex para [CMD:edit_file ...]
    edit_pattern = re.compile(r'\[CMD:edit_file\s+path="([^"]+)"\](.*?)\[/CMD\]', re.DOTALL)
    for match in edit_pattern.finditer(response):
        filepath = match.group(1)
        block_content = match.group(2)
        
        search_marker = "SEARCH:\n"
        replace_marker = "\nREPLACE:\n"
        
        if search_marker in block_content and replace_marker in block_content:
            s_idx = block_content.find(search_marker) + len(search_marker)
            r_idx = block_content.find(replace_marker)
            
            search_block = block_content[s_idx:r_idx]
            replace_block = block_content[r_idx + len(replace_marker):]
            
            res = edit_file(filepath, search_block, replace_block)
            if workspace_index:
                workspace_index.rebuild_index()
            results.append(res)
        else:
            results.append(f"Error: Edit block for {filepath} does not contain valid SEARCH/REPLACE tags.")

    # 4. Regex para [CMD:run_bash]
    bash_pattern = re.compile(r'\[CMD:run_bash\](.*?)\[/CMD\]', re.DOTALL)
    for match in bash_pattern.finditer(response):
        cmd = match.group(1).strip()
        res = execute_bash(cmd)
        results.append(res)

    # 5. Regex para [CMD:recall_memory ...]
    recall_pattern = re.compile(r'\[CMD:recall_memory\s+query="([^"]+)"\](.*?)\[/CMD\]', re.DOTALL)
    for match in recall_pattern.finditer(response):
        query = match.group(1)
        if memory_manager:
            res = memory_manager.retrieve_relevant_memory(query)
            if not res:
                res = "No relevant memory found."
            else:
                res = f"Memory recalled:\n{res}"
        else:
            res = "Error: Memory manager unavailable."
        results.append(res)

    # 6. Regex para [CMD:search_workspace ...]
    search_pattern = re.compile(r'\[CMD:search_workspace\s+query="([^"]+)"\](.*?)\[/CMD\]', re.DOTALL)
    for match in search_pattern.finditer(response):
        query = match.group(1)
        if workspace_index:
            matches = workspace_index.search(query, limit=5)
            if not matches:
                res = "No matching files found in the workspace."
            else:
                file_lines = [f"- {m[0]} (Score: {m[1]:.2f})" for m in matches]
                res = "Files found in the workspace:\n" + "\n".join(file_lines)
        else:
            res = "Error: Workspace indexer unavailable."
        results.append(res)

    return results
