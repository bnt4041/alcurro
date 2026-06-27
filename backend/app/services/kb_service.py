"""Base de conocimiento sobre los .md de docs/ — búsqueda por palabras clave.

Sin embeddings: ranking por solapamiento de términos (estilo whatsapp_nlu).
Usado por el asistente comercial del landing y la auto-resolución de tickets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.whatsapp_nlu import normalize_whatsapp_text

# docs/ está en la raíz del repo. En el contenedor el backend se monta en /app
# (con docs/ disponible en /app/docs) o, en desarrollo, junto al paquete.
_CANDIDATE_DIRS = [
    Path("/app/docs/soporte"),
    Path("/app/docs"),
    Path(__file__).resolve().parents[3] / "docs" / "soporte",
    Path(__file__).resolve().parents[3] / "docs",
]

# Palabras vacías frecuentes en español (ruido para el ranking)
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "ante", "con", "en", "para", "por", "que", "se", "su", "sus", "y", "o",
    "u", "e", "es", "son", "como", "mas", "pero", "si", "no", "lo", "le", "me",
    "te", "nos", "mi", "tu", "yo", "el", "ya", "muy", "este", "esta", "esto",
    "puedo", "puede", "como", "donde", "cuando", "hay", "tengo", "quiero",
    "necesito", "cuenta", "alcurro",
}

_MIN_SCORE = 2  # solapamiento mínimo de términos para considerar relevante


@dataclass
class KbArticle:
    title: str
    source: str  # nombre del fichero
    content: str
    _terms: set[str]


_cache: list[KbArticle] | None = None
_cache_signature: tuple | None = None


def _docs_dir() -> Path | None:
    for d in _CANDIDATE_DIRS:
        if d.is_dir():
            return d
    return None


def _tokenize(text: str) -> set[str]:
    norm = normalize_whatsapp_text(text)
    words = re.findall(r"[a-z0-9]{3,}", norm)
    return {w for w in words if w not in _STOPWORDS}


def _split_articles(md_text: str, source: str) -> list[KbArticle]:
    """Trocea un markdown por cabeceras de nivel 1-2; cada sección es un artículo."""
    lines = md_text.splitlines()
    articles: list[KbArticle] = []
    current_title = source.replace(".md", "").replace("-", " ").replace("_", " ")
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            articles.append(
                KbArticle(
                    title=current_title.strip(),
                    source=source,
                    content=body,
                    _terms=_tokenize(current_title + " " + body),
                )
            )

    for line in lines:
        m = re.match(r"^(#{1,2})\s+(.*)$", line)
        if m:
            flush()
            current_title = m.group(2).strip()
            buffer = []
        else:
            buffer.append(line)
    flush()
    return articles


def _signature(directory: Path) -> tuple:
    files = sorted(directory.glob("*.md"))
    return tuple((f.name, f.stat().st_mtime) for f in files)


def _load() -> list[KbArticle]:
    global _cache, _cache_signature
    directory = _docs_dir()
    if not directory:
        _cache, _cache_signature = [], None
        return []
    sig = _signature(directory)
    if _cache is not None and sig == _cache_signature:
        return _cache
    articles: list[KbArticle] = []
    for md in sorted(directory.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        articles.extend(_split_articles(text, md.name))
    _cache, _cache_signature = articles, sig
    return articles


@dataclass
class KbResult:
    title: str
    source: str
    snippet: str
    score: int


def search(query: str, limit: int = 3) -> list[KbResult]:
    """Devuelve los artículos más relevantes para la consulta (score >= _MIN_SCORE)."""
    terms = _tokenize(query)
    if not terms:
        return []
    scored: list[tuple[int, KbArticle]] = []
    for art in _load():
        score = len(terms & art._terms)
        if score >= _MIN_SCORE:
            scored.append((score, art))
    scored.sort(key=lambda x: x[0], reverse=True)
    results: list[KbResult] = []
    for score, art in scored[:limit]:
        snippet = art.content.strip()
        if len(snippet) > 600:
            snippet = snippet[:600].rsplit(" ", 1)[0] + "…"
        results.append(
            KbResult(title=art.title, source=art.source, snippet=snippet, score=score)
        )
    return results


def build_context(query: str, limit: int = 3) -> str:
    """Bloque de texto con los fragmentos relevantes para inyectar en el prompt IA."""
    results = search(query, limit=limit)
    if not results:
        return ""
    blocks = [f"### {r.title}\n{r.snippet}" for r in results]
    return "\n\n".join(blocks)
