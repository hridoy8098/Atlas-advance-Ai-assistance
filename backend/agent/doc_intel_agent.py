# backend/agent/doc_intel_agent.py — Document Intelligence Agent
# PDF/DOCX/TXT ingestion, local chunk index, retrieval-augmented Q&A with page citations.
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from .advanced_common import (
    ask,
    clean_text,
    data_file,
    fail,
    find_existing_path,
    ok,
    read_json,
    resolve_path,
    score_chunks,
    truncate,
    write_json,
)

INDEX_FILE = data_file("doc_index.json")
MAX_CHUNKS = 400
CHUNK_SIZE = 1400
CHUNK_OVERLAP = 180


class DocIntelAgent:
    name = "Document Intelligence Agent"

    def get_capabilities(self) -> List[str]:
        return ["doc_ingest", "doc_ask", "doc_list", "doc_remove", "doc_summary"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()

        try:
            if "list" in intent_lower:
                return self.list_documents()
            if "remove" in intent_lower or "delete" in intent_lower:
                return self.remove_document(str(entities.get("doc_id") or ""))

            target = self._resolve_doc(command, entities)
            question = str(entities.get("question") or entities.get("query") or "").strip()

            if not question:
                question = self._parse_question(command, target)
            if question and ("ask" in intent_lower or "question" in intent_lower or "?" in command or target is None):
                return self.ask(question, target)
            if target is not None:
                result = self.ingest(target)
                if not question and result.get("success"):
                    result["message"] += " এখন প্রশ্ন করলে page citation সহ উত্তর দেব।"
                return result
            return self.list_documents()
        except Exception as exc:
            return fail("doc_intel", f"Document Agent error: {exc}")

    # ---------------- ingestion ----------------
    def ingest(self, path: Path) -> Dict[str, Any]:
        if not path.exists() or not path.is_file():
            return fail("doc_intel", f"Document পাওয়া যায়নি: {path}")

        suffix = path.suffix.lower()
        if suffix not in (".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".log"):
            return fail("doc_intel", f"Unsupported format: {suffix}. PDF, DOCX, TXT, MD, CSV, JSON দিন।")

        try:
            digest = hashlib.sha1(path.read_bytes()).hexdigest()[:16]
        except Exception as exc:
            return fail("doc_intel", f"File hash করা যায়নি: {exc}")

        pages = self._extract_pages(path)
        if not pages:
            return fail("doc_intel", "Document থেকে text বের করা যায়নি (empty বা scanned PDF?)।")

        chunks: List[Dict[str, Any]] = []
        for page_number, page_text in pages:
            text = clean_text(page_text)
            if not text:
                continue
            start = 0
            while start < len(text) and len(chunks) < MAX_CHUNKS:
                piece = text[start:start + CHUNK_SIZE]
                chunks.append({
                    "id": len(chunks),
                    "page": page_number,
                    "text": piece,
                })
                start += CHUNK_SIZE - CHUNK_OVERLAP
            if len(chunks) >= MAX_CHUNKS:
                break

        index = read_json(INDEX_FILE, {"documents": {}})
        index.setdefault("documents", {})[digest] = {
            "doc_id": digest,
            "name": path.name,
            "path": str(path),
            "pages": len(pages),
            "chunks": chunks,
            "chars": sum(len(page[1]) for page in pages),
            "indexed_at": datetime.now().isoformat(timespec="seconds"),
        }
        write_json(INDEX_FILE, index)

        return ok(
            "doc_intel",
            f"📄 {path.name} indexed — {len(pages)} page(s), {len(chunks)} chunk(s).",
            doc_id=digest,
            name=path.name,
            pages=len(pages),
            chunks=len(chunks),
        )

    def ask(self, question: str, path: Optional[Path] = None) -> Dict[str, Any]:
        question = str(question or "").strip()
        if not question:
            return fail("doc_intel", "Question দিন, যেমন: “pdf theke ask koro: main finding ki?”")

        index = read_json(INDEX_FILE, {"documents": {}})
        documents = index.get("documents") or {}
        document = None

        if path is not None:
            try:
                digest = hashlib.sha1(path.read_bytes()).hexdigest()[:16]
            except Exception:
                digest = ""
            document = documents.get(digest)
            if document is None and path.exists():
                ingested = self.ingest(path)
                if not ingested.get("success"):
                    return ingested
                index = read_json(INDEX_FILE, {"documents": {}})
                documents = index.get("documents") or {}
                document = documents.get(ingested.get("doc_id"))
        elif documents:
            document = sorted(documents.values(), key=lambda item: item.get("indexed_at", ""), reverse=True)[0]

        if document is None:
            return fail("doc_intel", "কোন indexed document নেই। আগে PDF/DOCX path দিয়ে index করুন।")

        selected = score_chunks(document.get("chunks", []), question, limit=5)
        if not selected:
            return fail("doc_intel", "Document-এ প্রশ্নের সাথে মিলে এমন content পাওয়া যায়নি।")

        context = "\n\n".join(f"[page {chunk['page']}] {chunk['text']}" for chunk in selected)
        answer = ask(
            f"Answer the question using ONLY this document context.\nQuestion: {question}\n\n"
            f"Document: {document.get('name')}\nContext:\n{context}\n\n"
            "Cite pages as [p.N]. If the answer is absent, say so clearly. Reply in the user's language.",
            system_prompt="You are a precise document analyst. Never invent page numbers or facts.",
        )
        if not answer:
            answer = "AI unavailable. Most relevant excerpts:\n\n" + "\n\n".join(
                f"[p.{chunk['page']}] {truncate(chunk['text'], 700)}" for chunk in selected
            )

        return ok(
            "doc_intel",
            f"📄 Answer from {document.get('name')}.",
            answer=truncate(answer, 7000),
            document=document.get("name"),
            doc_id=document.get("doc_id"),
            pages_used=sorted({chunk["page"] for chunk in selected}),
            sources=[{"page": chunk["page"], "excerpt": truncate(chunk["text"], 260)} for chunk in selected],
        )

    def list_documents(self) -> Dict[str, Any]:
        documents = (read_json(INDEX_FILE, {"documents": {}}).get("documents") or {})
        items = [
            {
                "doc_id": doc.get("doc_id"),
                "name": doc.get("name"),
                "pages": doc.get("pages"),
                "chunks": len(doc.get("chunks", [])),
                "indexed_at": doc.get("indexed_at"),
            }
            for doc in sorted(documents.values(), key=lambda item: item.get("indexed_at", ""), reverse=True)
        ]
        return ok("doc_intel", f"📚 {len(items)} document(s) indexed.", documents=items)

    def remove_document(self, doc_id: str) -> Dict[str, Any]:
        index = read_json(INDEX_FILE, {"documents": {}})
        documents = index.get("documents") or {}
        if doc_id not in documents:
            return fail("doc_intel", "doc_id পাওয়া যায়নি।")
        removed = documents.pop(doc_id)
        write_json(INDEX_FILE, index)
        return ok("doc_intel", f"🗑️ Removed index for {removed.get('name')}.", doc_id=doc_id)

    # ---------------- extraction ----------------
    @staticmethod
    def _extract_pages(path: Path) -> List[tuple]:
        suffix = path.suffix.lower()
        pages: List[tuple] = []
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception as exc:
                raise RuntimeError(f"pypdf missing: {exc}")
            reader = PdfReader(str(path))
            for index, page in enumerate(reader.pages, 1):
                try:
                    pages.append((index, page.extract_text() or ""))
                except Exception:
                    pages.append((index, ""))
        elif suffix == ".docx":
            try:
                from docx import Document
            except Exception as exc:
                raise RuntimeError(f"python-docx missing: {exc}")
            document = Document(str(path))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            for table in document.tables:
                for row in table.rows:
                    text += "\n" + " | ".join(cell.text for cell in row.cells)
            pages.append((1, text))
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
            pages.append((1, text))
        return pages

    # ---------------- parsing ----------------
    @staticmethod
    def _resolve_doc(command: str, entities: Dict[str, Any]) -> Optional[Path]:
        raw = entities.get("path") or entities.get("file") or entities.get("document")
        if raw:
            return resolve_path(raw)
        return find_existing_path(command)

    @staticmethod
    def _parse_question(command: str, target: Optional[Path]) -> str:
        text = str(command or "").strip()
        if target is not None:
            text = text.replace(str(target), " ")
            text = text.replace(target.name, " ")
        text = re.sub(
            r"(?i)\b(?:pdf|docx|document|doc|ask|question|theke|from|analyze|analyse|summary|summarize|bolo|জিজ্ঞাসা|জানতে চাই)\b",
            " ",
            text,
        )
        return clean_text(text).strip(" :,-")

    def test(self) -> Dict[str, Any]:
        loaded = read_json(INDEX_FILE, {"documents": {}}).get("documents") or {}
        try:
            import pypdf  # noqa: F401
            pypdf_ok = True
        except Exception:
            pypdf_ok = False
        try:
            import docx  # noqa: F401
            docx_ok = True
        except Exception:
            docx_ok = False
        return {
            "success": True,
            "agent": "doc_intel",
            "documents": len(loaded),
            "pypdf": pypdf_ok,
            "docx": docx_ok,
            "message": "Document Intelligence ready.",
        }


doc_intel_agent = DocIntelAgent()
