"""
Unit and Integration Tests for Semantic Memory (RAG) and ChromaDB Engine.
Verifies vector persistence, text chunking with line offsets, folder indexing,
and "Where did I write about X?" semantic location queries.
"""

import os
from pathlib import Path
import pytest

from memory.vector_store import (
    VectorMemoryStore,
    chunk_text,
)
from tools.semantic_memory_tool import SemanticMemoryTool


class TestTextChunker:
    """Test character and line tracking chunking mechanism."""

    def test_chunk_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   \n\t  ") == []

    def test_chunk_single_short_string(self):
        text = "Hello JARVIS, this is a short test note."
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["line_start"] == 1
        assert chunks[0]["line_end"] == 1

    def test_chunk_multiline_overlapping_offsets(self):
        lines = [f"Line {i}: This is some interesting content about project architecture." for i in range(1, 30)]
        text = "\n".join(lines)
        chunks = chunk_text(text, chunk_size=150, overlap=40)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["line_start"] >= 1
            assert chunk["line_end"] >= chunk["line_start"]
            assert len(chunk["text"]) > 0


class TestVectorMemoryStore:
    """Test ChromaDB store persistence, embedding, and semantic query matching."""

    @pytest.fixture
    def temp_store(self, tmp_path):
        """Create an isolated VectorMemoryStore in a temporary directory."""
        store_path = tmp_path / "test_chroma"
        store = VectorMemoryStore(db_dir=store_path)
        yield store

    def test_add_and_query_note(self, temp_store):
        success = temp_store.add_note(
            note_id="apollo_note",
            title="Project Apollo",
            content="Project Apollo requires high altitude orbital trajectory recalculations.",
            tags=["aerospace"]
        )
        assert success is True

        # Query by semantic concept (not literal keywords)
        results = temp_store.query_notes("satellite rocket flight path", n_results=3)
        assert len(results) >= 1
        assert "trajectory" in results[0]["content"].lower() or "orbital" in results[0]["content"].lower()

    def test_add_and_query_chat_turns(self, temp_store):
        res1 = temp_store.add_chat_turn(
            turn_id="turn_1",
            role="user",
            content="Jarvis, remember that my favorite color is deep obsidian blue."
        )
        res2 = temp_store.add_chat_turn(
            turn_id="turn_2",
            role="assistant",
            content="Understood, sir. Recorded obsidian blue as your preference."
        )
        assert res1 is True
        assert res2 is True

        # Semantic query
        interactions = temp_store.query_chat_history("what color do I like?", n_results=2)
        assert len(interactions) >= 1
        assert any("obsidian blue" in item["content"].lower() for item in interactions)

    def test_index_folder_and_where_did_i_write(self, temp_store, tmp_path):
        docs_dir = tmp_path / "my_workspace_notes"
        docs_dir.mkdir()

        doc1 = docs_dir / "quantum_computing.md"
        doc1.write_text(
            "# Quantum Computing\n\n"
            "We are utilizing superconducting qubits with Josephson junctions.\n"
            "Error mitigation relies on surface code quantum error correction.\n",
            encoding="utf-8"
        )

        doc2 = docs_dir / "cooking_recipes.txt"
        doc2.write_text(
            "Italian Pizza Dough Recipe:\n"
            "500g 00 flour, 320g water, 3g dry yeast, 10g salt.\n"
            "Ferment for 48 hours at room temperature.\n",
            encoding="utf-8"
        )

        # Index folder
        summary = temp_store.index_folder(docs_dir)
        assert summary["files_indexed"] == 2
        assert summary["total_chunks"] >= 2

        # Semantic question: Where did I write about X?
        res = temp_store.where_did_i_write("superconducting circuits and error correction")
        assert res["found"] is True
        formatted = res["formatted_answer"]
        assert "quantum_computing.md" in formatted
        assert "qubits" in formatted.lower() or "josephson" in formatted.lower()

        # Query cooking
        pizza_res = temp_store.where_did_i_write("how much flour for pizza dough?")
        assert pizza_res["found"] is True
        pizza_formatted = pizza_res["formatted_answer"]
        assert "cooking_recipes.txt" in pizza_formatted
        assert "500g" in pizza_formatted


class TestSemanticMemoryTool:
    """Test SemanticMemoryTool adhering to BaseTool interface contract."""

    @pytest.fixture
    def memory_tool(self, tmp_path, monkeypatch):
        isolated_store = VectorMemoryStore(db_dir=tmp_path / "tool_chroma")
        monkeypatch.setattr(VectorMemoryStore, "get_instance", classmethod(lambda cls: isolated_store))
        tool = SemanticMemoryTool()
        return tool

    def test_tool_save_note_and_search(self, memory_tool):
        # Save note action
        res = memory_tool.run(
            action="save_note",
            title="Garage Passcode",
            content="The secret garage passcode is 8492 delta."
        )
        assert res.success is True
        assert "saved" in res.message.lower()

        # Search memory action
        search_res = memory_tool.run(
            action="search_memory",
            query="garage code or password"
        )
        assert search_res.success is True
        assert len(search_res.data["notes"]) >= 1
        assert "8492" in search_res.data["notes"][0]["content"]

    def test_tool_index_and_where_did_i_write(self, memory_tool, tmp_path):
        test_dir = tmp_path / "notes_folder"
        test_dir.mkdir()
        file_a = test_dir / "budget_2026.md"
        file_a.write_text(
            "Q3 2026 Marketing allocation is 45,000 USD.\n"
            "R&D expenditure is projected at 120,000 USD.\n",
            encoding="utf-8"
        )

        idx_res = memory_tool.run(
            action="index_folder",
            folder_path=str(test_dir)
        )
        assert idx_res.success is True
        assert idx_res.data["files_indexed"] >= 1

        loc_res = memory_tool.run(
            action="where_did_i_write",
            query="marketing and research budget allocation"
        )
        assert loc_res.success is True
        assert "budget_2026.md" in loc_res.message
        assert "45,000" in loc_res.message or "120,000" in loc_res.message
