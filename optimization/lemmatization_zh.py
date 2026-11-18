"""中文感知的 BM25 预处理（替换 mem0/utils/lemmatization.py）。

原版用 spaCy 英文词形还原：中文整句被当成一个巨型 token，
pgvector 的 to_tsvector('simple', text_lemmatized) 无法切词，
BM25 关键词通道对中文完全失效。

本版：检测到 CJK 字符时用 jieba 分词 + 停用词过滤；
纯英文仍走原 spaCy 路径。add 与 search 共用此函数，
写入 payload 的 text_lemmatized 和查询侧自动保持一致。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ZH_STOPWORDS = {
    "的", "了", "吗", "呢", "吧", "啊", "是", "在", "和", "与", "就", "都",
    "也", "很", "还", "又", "才", "只", "对", "跟", "给", "让", "被", "把",
    "从", "到", "向", "往", "之", "其", "此", "该", "每", "各", "没", "不",
    "么", "请", "一下", "一个", "一些", "这个", "那个", "这些", "那些",
    "这里", "那里", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "什么", "怎么", "怎样", "如何", "哪", "哪里", "哪个", "谁", "多少",
    "为什么", "为啥", "帮我", "记得", "知道",
}


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _zh_tokenize(text: str) -> str:
    import jieba

    tokens = []
    for tok in jieba.lcut(text.lower()):
        tok = tok.strip()
        if not tok or tok in _ZH_STOPWORDS or not tok.isalnum():
            continue
        tokens.append(tok)
    return " ".join(tokens)


def lemmatize_for_bm25(text: str) -> str:
    """Lemmatize text for BM25 matching (Chinese-aware).

    Returns space-joined tokens for full-text search.
    """
    if _has_cjk(text):
        return _zh_tokenize(text)

    from mem0.utils.spacy_models import get_nlp_lemma

    nlp = get_nlp_lemma()
    if nlp is None:
        return text

    doc = nlp(text.lower())
    tokens = []

    for token in doc:
        if token.is_punct or token.is_stop:
            continue

        lemma = token.lemma_
        if lemma.isalnum():
            tokens.append(lemma)

        if token.text.endswith("ing") and token.text != lemma and token.text.isalnum():
            tokens.append(token.text)

    return " ".join(tokens)