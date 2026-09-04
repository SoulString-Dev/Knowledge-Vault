"""RRF 融合纯函数测试。"""

import pytest

from app.services.search import SearchHit, rrf_merge


def _hit(aid: int, path: str) -> SearchHit:
    return SearchHit(
        article_id=aid,
        title=f"t{aid}",
        url=f"u{aid}",
        status="ready",
        score=0.0,
        snippet=None,
        matched_by=[path],
    )


def test_rrf_scores_and_merge() -> None:
    kw = [_hit(1, "keyword"), _hit(2, "keyword")]
    se = [_hit(2, "semantic"), _hit(3, "semantic")]
    merged = rrf_merge(kw, se)
    ids = [h.article_id for h in merged]
    # 文章 2 两路都命中，得分最高
    assert ids[0] == 2
    top = merged[0]
    assert top.matched_by == ["keyword", "semantic"]
    assert top.score == pytest.approx(1.0 / (60 + 2) + 1.0 / (60 + 1))


def test_rrf_single_source_order() -> None:
    merged = rrf_merge([_hit(5, "keyword"), _hit(7, "keyword")], [])
    assert [h.article_id for h in merged] == [5, 7]
    assert merged[0].score > merged[1].score
