"""
ChromaDB Persistent Vector Memory Store and Semantic RAG Engine for Project JARVIS.
Author: Pair A / Rohit & Jay

Capabilities:
1. Persistent vector embedding store for notes, chat history, and workspace files.
2. Intelligent text chunking with line number tracking and overlap.
3. Folder indexing: recursively crawls folders and indexes files (.txt, .md, .py, .pdf, .docx, etc.).
4. Semantic retrieval: retrieves notes, memories, and documents by meaning instead of exact keywords.
5. "Where did I write about X?" semantic locator with file paths, line ranges, and matched snippets.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Union

logger = logging.getLogger(__name__)

# Default vector store path
_DEFAULT_CHROMA_PATH = Path("memory") / "chroma_db"

# File extensions supported for semantic indexing
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".html", ".css", ".csv", ".rst",
    ".pdf", ".docx", ".c", ".cpp", ".h", ".cs", ".java", ".go", ".rs"
}


def chunk_text(
    text: str,
    chunk_size: int = 700,
    overlap: int = 150
) -> List[Dict[str, Any]]:
    """Chunks text into overlapping passages while tracking character and line offsets.

    Args:
        text: Input string to chunk.
        chunk_size: Target character length per chunk (default: 700).
        overlap: Character overlap between consecutive chunks (default: 150).

    Returns:
        List of dictionaries with 'text', 'chunk_index', 'line_start', 'line_end'.
    """
    if not text or not str(text).strip():
        return []

    clean_text = str(text)
    total_len = len(clean_text)

    # Pre-calculate line start offsets for line number lookup
    lines = clean_text.splitlines(keepends=True)
    line_offsets: List[int] = []
    current_off = 0
    for l in lines:
        line_offsets.append(current_off)
        current_off += len(l)

    def _offset_to_line(offset: int) -> int:
        """Find 1-based line number for a character offset."""
        low, high = 0, len(line_offsets) - 1
        res = 0
        while low <= high:
            mid = (low + high) // 2
            if line_offsets[mid] <= offset:
                res = mid
                low = mid + 1
            else:
                high = mid - 1
        return res + 1

    chunks: List[Dict[str, Any]] = []
    start = 0
    chunk_idx = 0

    while start < total_len:
        end = min(start + chunk_size, total_len)

        # Try to break at a natural boundary (newline or period) if not at the very end
        if end < total_len:
            lookback = clean_text.rfind("\n\n", start, end)
            if lookback == -1 or lookback <= start + (chunk_size // 3):
                lookback = clean_text.rfind("\n", start, end)
            if lookback == -1 or lookback <= start + (chunk_size // 3):
                lookback = clean_text.rfind(". ", start, end)
            if lookback != -1 and lookback > start + (chunk_size // 3):
                end = lookback + 1

        chunk_str = clean_text[start:end].strip()
        if chunk_str:
            line_start = _offset_to_line(start)
            line_end = _offset_to_line(max(start, end - 1))
            chunks.append({
                "chunk_index": chunk_idx,
                "text": chunk_str,
                "start_char": start,
                "end_char": end,
                "line_start": line_start,
                "line_end": line_end,
            })
            chunk_idx += 1

        if end >= total_len:
            break
        start = max(start + 1, end - overlap)

    return chunks


def _extract_file_text(file_path: Path) -> str:
    """Safely extracts plain text content from various file types."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(f"--- Page {idx + 1} ---\n{txt}")
            return "\n\n".join(pages_text)
        except Exception as e:
            logger.debug("Failed to extract PDF text from %s: %s", file_path, e)
            return ""

    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.debug("Failed to extract DOCX text from %s: %s", file_path, e)
            return ""

    else:
        # Standard text-based formats
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            try:
                return file_path.read_text(encoding="latin-1", errors="replace")
            except Exception as e:
                logger.debug("Failed to read text from %s: %s", file_path, e)
                return ""


class VectorMemoryStore:
    """Persistent ChromaDB vector database manager for RAG memory and codebase indexing."""

    _instance: Optional[VectorMemoryStore] = None

    @classmethod
    def get_instance(cls, db_dir: Optional[Union[str, Path]] = None) -> VectorMemoryStore:
        """Singleton accessor for VectorMemoryStore."""
        if cls._instance is None:
            cls._instance = cls(db_dir=db_dir)
        return cls._instance

    def __init__(self, db_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize ChromaDB client and default collections."""
        self.db_dir = Path(db_dir) if db_dir else _DEFAULT_CHROMA_PATH
        self.db_dir.mkdir(parents=True, exist_ok=True)

        import chromadb
        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=str(self.db_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        # 1. Collection for user notes & memories
        self.notes_collection = self.client.get_or_create_collection(
            name="jarvis_notes",
            metadata={"description": "Persistent user notes and memory snippets"}
        )

        # 2. Collection for conversation chat history
        self.chat_collection = self.client.get_or_create_collection(
            name="jarvis_chat_history",
            metadata={"description": "Conversation turns and semantic dialogue recall"}
        )

        # 3. Collection for indexed folders, documents, and workspace files
        self.workspace_collection = self.client.get_or_create_collection(
            name="jarvis_workspace_docs",
            metadata={"description": "Semantic index of codebase and user document folders"}
        )

    # --------------------------------------------------------------------------
    # Notes Semantic Indexing & Querying
    # --------------------------------------------------------------------------
    def add_note(
        self,
        note_id: Union[int, str],
        title: str,
        content: str,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Store or update a note in the vector database for semantic retrieval."""
        try:
            full_text = f"Title: {title.strip()}\n\n{content.strip()}"
            doc_id = f"note_{note_id}"
            metadata = {
                "note_id": str(note_id),
                "title": title.strip(),
                "type": "note",
                "timestamp": time.time(),
                "tags": ",".join(tags) if tags else "",
            }
            self.notes_collection.upsert(
                ids=[doc_id],
                documents=[full_text],
                metadatas=[metadata]
            )
            return True
        except Exception as exc:
            logger.error("Failed to add note to vector store: %s", exc)
            return False

    def query_notes(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search notes semantically by query meaning instead of exact keywords."""
        if not query or not query.strip():
            return []
        try:
            res = self.notes_collection.query(
                query_texts=[query.strip()],
                n_results=min(n_results, max(1, self.notes_collection.count()))
            )
            out = []
            if res and res.get("documents") and res["documents"][0]:
                docs = res["documents"][0]
                metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs)
                distances = res["distances"][0] if res.get("distances") else [0.0] * len(docs)
                ids = res["ids"][0] if res.get("ids") else [""] * len(docs)

                for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
                    # Chroma cosine/L2 distance conversion to approximate similarity (0.0 to 1.0)
                    sim = max(0.0, min(1.0, 1.0 - (dist / 2.0))) if dist is not None else 1.0
                    out.append({
                        "id": doc_id,
                        "title": meta.get("title", "Untitled Note"),
                        "content": doc,
                        "note_id": meta.get("note_id"),
                        "similarity": round(sim, 3),
                        "distance": round(dist, 4) if dist is not None else 0.0,
                    })
            return out
        except Exception as exc:
            logger.error("Error querying semantic notes: %s", exc)
            return []

    # --------------------------------------------------------------------------
    # Chat History Semantic Recall
    # --------------------------------------------------------------------------
    def add_chat_turn(
        self,
        turn_id: str,
        role: str,
        content: str,
        timestamp: Optional[float] = None
    ) -> bool:
        """Store a chat message turn in vector memory."""
        try:
            doc_id = f"chat_{turn_id}"
            metadata = {
                "role": role,
                "timestamp": timestamp or time.time(),
                "type": "chat_history",
            }
            self.chat_collection.upsert(
                ids=[doc_id],
                documents=[f"{role.capitalize()}: {content.strip()}"],
                metadatas=[metadata]
            )
            return True
        except Exception as exc:
            logger.debug("Failed to add chat turn to vector store: %s", exc)
            return False

    def query_chat_history(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant past conversation turns by semantic meaning."""
        if not query or not query.strip():
            return []
        try:
            count = self.chat_collection.count()
            if count == 0:
                return []
            res = self.chat_collection.query(
                query_texts=[query.strip()],
                n_results=min(n_results, count)
            )
            out = []
            if res and res.get("documents") and res["documents"][0]:
                for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
                    out.append({
                        "role": meta.get("role", "unknown"),
                        "content": doc,
                        "timestamp": meta.get("timestamp", 0.0),
                    })
            return out
        except Exception as exc:
            logger.debug("Error querying chat history vector store: %s", exc)
            return []

    # --------------------------------------------------------------------------
    # Folder & Codebase Indexing
    # --------------------------------------------------------------------------
    def index_folder(
        self,
        folder_path: Union[str, Path],
        glob_pattern: str = "*",
        recursive: bool = True,
        max_files: int = 300
    ) -> Dict[str, Any]:
        """Indexes all readable documents and code files inside a folder into ChromaDB.

        Args:
            folder_path: Target directory path to index.
            glob_pattern: File glob match pattern (default: '*').
            recursive: Whether to traverse subdirectories recursively (default: True).
            max_files: Cap on maximum files to index in a single run (default: 300).

        Returns:
            Dict containing indexed files count, total chunks, and list of files.
        """
        target_dir = Path(folder_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Directory not found: '{folder_path}'")

        # Skip unwanted system/heavy build directories
        ignore_dirs = {
            ".git", "node_modules", "__pycache__", "venv", ".venv",
            "build", "dist", ".pytest_cache", "chroma_db", ".gemini"
        }

        matched_files: List[Path] = []
        iterator = target_dir.rglob(glob_pattern) if recursive else target_dir.glob(glob_pattern)

        for p in iterator:
            if not p.is_file():
                continue
            # Check directory exclusion
            if any(part in ignore_dirs for part in p.parts):
                continue
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                matched_files.append(p)
                if len(matched_files) >= max_files:
                    break

        total_chunks = 0
        indexed_file_names: List[str] = []

        batch_ids: List[str] = []
        batch_docs: List[str] = []
        batch_metas: List[Dict[str, Any]] = []

        for file_p in matched_files:
            try:
                content = _extract_file_text(file_p)
                if not content or len(content.strip()) < 10:
                    continue

                chunks = chunk_text(content, chunk_size=750, overlap=120)
                if not chunks:
                    continue

                rel_path = str(file_p.relative_to(target_dir))
                indexed_file_names.append(rel_path)

                for chunk in chunks:
                    chunk_id = hashlib.sha256(
                        f"{file_p.resolve()}#{chunk['chunk_index']}".encode("utf-8")
                    ).hexdigest()[:24]

                    batch_ids.append(f"doc_{chunk_id}")
                    batch_docs.append(chunk["text"])
                    batch_metas.append({
                        "file_path": str(file_p.resolve()),
                        "file_name": file_p.name,
                        "rel_path": rel_path,
                        "folder": str(target_dir),
                        "chunk_index": chunk["chunk_index"],
                        "line_start": chunk["line_start"],
                        "line_end": chunk["line_end"],
                        "timestamp": file_p.stat().st_mtime,
                    })

                total_chunks += len(chunks)

                # Commit in batches of 100 to prevent large memory spikes
                if len(batch_ids) >= 100:
                    self.workspace_collection.upsert(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metas
                    )
                    batch_ids.clear()
                    batch_docs.clear()
                    batch_metas.clear()

            except Exception as file_err:
                logger.warning("Could not index file '%s': %s", file_p, file_err)

        if batch_ids:
            self.workspace_collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas
            )

        return {
            "success": True,
            "folder": str(target_dir),
            "files_indexed": len(indexed_file_names),
            "total_chunks": total_chunks,
            "indexed_files": indexed_file_names[:25],
        }

    # --------------------------------------------------------------------------
    # "Where did I write about X?" Semantic Locator
    # --------------------------------------------------------------------------
    def where_did_i_write(
        self,
        query: str,
        folder_path: Optional[str] = None,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """Answers 'where did I write about X?' by querying semantic memory and indexed files.

        Returns exact file paths, line ranges, matching snippets, and relevance scores.
        """
        if not query or not query.strip():
            return {
                "found": False,
                "query": query,
                "matches": [],
                "formatted_answer": "Please specify what topic or phrase you are searching for."
            }

        clean_query = query.strip()
        matches: List[Dict[str, Any]] = []

        # 1. Search indexed files and workspace
        try:
            ws_count = self.workspace_collection.count()
            if ws_count > 0:
                where_filter = None
                if folder_path:
                    norm_folder = str(Path(folder_path).resolve())
                    where_filter = {"folder": norm_folder}

                kwargs: Dict[str, Any] = {
                    "query_texts": [clean_query],
                    "n_results": min(n_results * 2, ws_count),
                }
                if where_filter:
                    kwargs["where"] = where_filter

                res = self.workspace_collection.query(**kwargs)

                if res and res.get("documents") and res["documents"][0]:
                    docs = res["documents"][0]
                    metas = res["metadatas"][0]
                    distances = res["distances"][0] if res.get("distances") else [0.0] * len(docs)

                    for doc, meta, dist in zip(docs, metas, distances):
                        sim = max(0.0, min(1.0, 1.0 - (dist / 2.0))) if dist is not None else 1.0
                        matches.append({
                            "type": "file",
                            "file_path": meta.get("file_path", ""),
                            "file_name": meta.get("file_name", ""),
                            "rel_path": meta.get("rel_path", ""),
                            "line_start": meta.get("line_start", 1),
                            "line_end": meta.get("line_end", 1),
                            "snippet": doc,
                            "similarity": round(sim, 3),
                            "score": sim,
                        })
        except Exception as ws_err:
            logger.debug("Error searching workspace collection: %s", ws_err)

        # 2. Search notes collection
        try:
            notes_results = self.query_notes(clean_query, n_results=n_results)
            for n in notes_results:
                matches.append({
                    "type": "note",
                    "title": n["title"],
                    "note_id": n.get("note_id"),
                    "file_path": f"Note #{n.get('note_id')} ({n['title']})",
                    "snippet": n["content"],
                    "line_start": 1,
                    "line_end": len(n["content"].splitlines()),
                    "similarity": n["similarity"],
                    "score": n["similarity"],
                })
        except Exception as note_err:
            logger.debug("Error searching notes in where_did_i_write: %s", note_err)

        # Sort matches by similarity score descending
        matches.sort(key=lambda m: m.get("score", 0.0), reverse=True)
        top_matches = matches[:n_results]

        if not top_matches:
            formatted = (
                f"I could not find any notes or indexed files discussing '{clean_query}'. "
                "You can index a folder using: `index folder <path>` to make it searchable."
            )
            return {
                "found": False,
                "query": clean_query,
                "matches": [],
                "formatted_answer": formatted
            }

        answer_lines = [f"Found {len(top_matches)} relevant locations discussing '{clean_query}':\n"]
        for idx, m in enumerate(top_matches, 1):
            if m["type"] == "file":
                loc = f"{m.get('rel_path') or m.get('file_name')} (Lines {m['line_start']}–{m['line_end']})"
                answer_lines.append(f"{idx}. [File] {loc} (Relevance: {int(m['similarity'] * 100)}%):")
                preview = m['snippet'].replace("\n", " ")
                if len(preview) > 180:
                    preview = preview[:180] + "..."
                answer_lines.append(f"   \"{preview}\"\n   Path: {m['file_path']}\n")
            else:
                answer_lines.append(f"{idx}. [Note] {m['title']} (Relevance: {int(m['similarity'] * 100)}%):")
                preview = m['snippet'].replace("\n", " ")
                if len(preview) > 180:
                    preview = preview[:180] + "..."
                answer_lines.append(f"   \"{preview}\"\n")

        return {
            "found": True,
            "query": clean_query,
            "matches": top_matches,
            "formatted_answer": "\n".join(answer_lines).strip()
        }
