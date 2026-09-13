from __future__ import annotations

import re
from pathlib import Path

from app.config import settings
from app.db import get_connection


GENERIC_TERMS = {
    "现场", "场有", "有异", "异响", "响但", "但没", "没有", "有故", "故障", "障码",
    "请问", "怎么", "如何", "应该", "需要", "帮我", "先看", "是否", "以及", "然后",
}
HIGH_SIGNAL_TERMS = {"温度", "离线", "高风险", "传感器", "制冷", "网络"}


def _terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[A-Za-z0-9-]+|[\u4e00-\u9fff]+", query):
        token = token.lower()
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            if len(token) == 1:
                terms.append(token)
            else:
                terms.extend(token[index : index + 2] for index in range(len(token) - 1))
        else:
            terms.append(token)
    return list(
        dict.fromkeys(
            term for term in terms if term.strip() and term not in GENERIC_TERMS
        )
    )


def index_knowledge_documents(database_path: str, directory: str) -> int:
    from data.seed import _chunks

    connection = get_connection(database_path)
    count = 0
    try:
        for document_path in sorted(Path(directory).glob("*.md")):
            document_id = f"doc-{document_path.stem}"
            connection.execute(
                "INSERT OR IGNORE INTO knowledge_documents "
                "(document_id, source_name, source_type, is_demo_data) VALUES (?, ?, ?, 1)",
                (document_id, document_path.name, "markdown_demo"),
            )
            for index, (_, section, content) in enumerate(
                _chunks(document_path.read_text(encoding="utf-8")), start=1
            ):
                chunk_id = f"{document_id}-{index:03d}"
                connection.execute("DELETE FROM knowledge_fts WHERE chunk_id = ?", (chunk_id,))
                connection.execute(
                    "INSERT OR REPLACE INTO knowledge_chunks "
                    "(chunk_id, document_id, content, source_section, source_page, is_demo_data) "
                    "VALUES (?, ?, ?, ?, ?, 1)",
                    (chunk_id, document_id, content, section, str(index)),
                )
                connection.execute(
                    "INSERT INTO knowledge_fts "
                    "(chunk_id, content, source_name, source_section) VALUES (?, ?, ?, ?)",
                    (chunk_id, content, document_path.name, section),
                )
                count += 1
        connection.commit()
        return count
    finally:
        connection.close()


def _row_result(row, score: float) -> dict:
    return {
        "chunk_id": row["chunk_id"],
        "content": row["content"],
        "source_name": row["source_name"],
        "source_section": row["source_section"],
        "score": round(score, 3),
    }


def _content_score(content: str, terms: list[str], base: float) -> float:
    content_lower = content.lower()
    matched_terms = {term for term in terms if term in content_lower}
    score = min(0.98, base + len(matched_terms) / max(len(terms), 1) * (1 - base))
    has_explicit_code = any(re.fullmatch(r"e\d{2}", term) for term in matched_terms)
    has_domain_signal = bool(matched_terms & HIGH_SIGNAL_TERMS)
    if has_domain_signal:
        score = max(score, 0.55)
    if len(matched_terms) < 2 and not has_explicit_code:
        return min(score, 0.45) if not has_domain_signal else score
    return score


def search_service_knowledge(query: str, limit: int = 5) -> list[dict]:
    terms = _terms(query)
    if not terms:
        return []
    connection = get_connection(settings.database_path)
    try:
        match_query = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms[:12])
        rows = connection.execute(
            "SELECT chunk_id, content, source_name, source_section, bm25(knowledge_fts) AS rank "
            "FROM knowledge_fts WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
            (match_query, limit),
        ).fetchall()
        results = []
        for row in rows:
            score = _content_score(row["content"], terms, base=0.35)
            results.append(_row_result(row, score))
        if results:
            return results

        like_conditions = " OR ".join("content LIKE ?" for _ in terms[:8])
        params = [f"%{term}%" for term in terms[:8]]
        fallback_rows = connection.execute(
            "SELECT chunk_id, content, source_name, source_section FROM knowledge_fts "
            f"WHERE {like_conditions}",
            params,
        ).fetchall()
        ranked = sorted(
            (
                _row_result(row, _content_score(row["content"], terms, base=0.25))
                for row in fallback_rows
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        return ranked[:limit]
    finally:
        connection.close()
