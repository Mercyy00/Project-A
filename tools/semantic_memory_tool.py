"""
Semantic Memory and Workspace RAG Tool for Project JARVIS.
Author: Abhijit & Rohit (Pair A & C integration)

Exposes BaseTool interfaces for:
1. Semantic memory search (search notes & conversations by concept instead of exact keywords).
2. Folder and codebase indexing into ChromaDB vector database.
3. 'Where did I write about X?' locator with file paths, line ranges, and relevance scoring.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class SemanticMemoryTool(BaseTool):
    """Tool for semantic memory retrieval, folder indexing, and 'where did I write' RAG lookups."""

    name: str = "semantic_memory"
    description: str = (
        "Semantic memory and RAG tool. Retrieve notes and conversations by meaning instead of exact keywords, "
        "index folders or codebases into vector storage, or ask 'where did I write about X?' to get exact files and lines."
    )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_memory", "index_folder", "where_did_i_write", "save_note"],
                        "description": (
                            "The semantic action to perform: "
                            "'search_memory' (search notes/chat semantically), "
                            "'index_folder' (index folder files into vector database), "
                            "'where_did_i_write' (find where a topic was written across files/notes), "
                            "or 'save_note' (persist a note with vector embeddings)."
                        )
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query or question (e.g. 'project architecture', 'docker setup', 'where did I write about authentication?')."
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "Folder path to index or constrain search to (e.g. 'docs', 'src', '.')."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of note when action is 'save_note'."
                    },
                    "content": {
                        "type": "string",
                        "description": "Body content of note when action is 'save_note'."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)."
                    }
                },
                "required": ["action"]
            }
        }

    def run(
        self,
        action: str = "search_memory",
        query: Optional[str] = None,
        folder_path: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        limit: int = 5,
        **kwargs: Any
    ) -> ToolResult:
        """Executes semantic memory and indexing operations."""
        act = action.strip().lower()

        try:
            from memory.vector_store import VectorMemoryStore
            store = VectorMemoryStore.get_instance()
        except Exception as store_err:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to initialize ChromaDB vector store: {store_err}"
            )

        # ----------------------------------------------------------------------
        # 1. Where did I write about X?
        # ----------------------------------------------------------------------
        if act in ("where_did_i_write", "find_written", "locate"):
            if not query or not query.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Please provide a query for 'where did I write about X?'."
                )

            res = store.where_did_i_write(
                query=query.strip(),
                folder_path=folder_path,
                n_results=limit
            )
            return ToolResult(
                success=res.get("found", False),
                data=res.get("matches", []),
                message=res.get("formatted_answer", "No matches found.")
            )

        # ----------------------------------------------------------------------
        # 2. Index Folder
        # ----------------------------------------------------------------------
        elif act in ("index_folder", "index", "crawl"):
            target = folder_path or query or "."
            target_path = Path(target).resolve()
            if not target_path.exists():
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Folder not found: '{target}'"
                )

            try:
                index_summary = store.index_folder(
                    folder_path=target_path,
                    recursive=True
                )
                msg = (
                    f"Successfully indexed folder '{target_path.name}'. "
                    f"Processed {index_summary['files_indexed']} files into {index_summary['total_chunks']} semantic chunks. "
                    "You can now ask 'where did I write about X?' or search it semantically."
                )
                return ToolResult(
                    success=True,
                    data=index_summary,
                    message=msg
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Error indexing folder '{target}': {e}"
                )

        # ----------------------------------------------------------------------
        # 3. Search Memory (Notes & Chat)
        # ----------------------------------------------------------------------
        elif act in ("search_memory", "search", "query"):
            if not query or not query.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Query parameter is required for semantic search."
                )

            notes = store.query_notes(query.strip(), n_results=limit)
            chat = store.query_chat_history(query.strip(), n_results=limit)

            combined_count = len(notes) + len(chat)
            if combined_count == 0:
                return ToolResult(
                    success=True,
                    data={"notes": [], "chat": []},
                    message=f"No semantic memories found matching '{query.strip()}'."
                )

            summary_lines = [f"Found {combined_count} semantic memory matches for '{query.strip()}':"]
            for idx, n in enumerate(notes, 1):
                summary_lines.append(f"- [Note] {n['title']} ({int(n['similarity'] * 100)}% match): {n['content'][:150]}...")
            for idx, c in enumerate(chat, 1):
                summary_lines.append(f"- [Chat] {c['role'].capitalize()}: {c['content'][:150]}...")

            return ToolResult(
                success=True,
                data={"notes": notes, "chat": chat},
                message="\n".join(summary_lines)
            )

        # ----------------------------------------------------------------------
        # 4. Save Note
        # ----------------------------------------------------------------------
        elif act in ("save_note", "store_note"):
            n_title = title or (query if query else "Quick Note")
            n_content = content or query or ""
            if not n_content.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Note content cannot be empty."
                )

            import time
            note_id = int(time.time())
            saved = store.add_note(note_id=note_id, title=n_title.strip(), content=n_content.strip())
            if saved:
                return ToolResult(
                    success=True,
                    data={"note_id": note_id, "title": n_title},
                    message=f"Saved note '{n_title}' into persistent memory and ChromaDB vector store."
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Failed to save note to vector store."
                )

        else:
            return ToolResult(
                success=False,
                data=None,
                message=f"Unknown semantic memory action '{action}'. Supported: search_memory, index_folder, where_did_i_write, save_note."
            )
