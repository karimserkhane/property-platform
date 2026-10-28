"""Read-only evaluation of the evidence search on the published statements (E01).

Each case pairs a query with a relevance rule over the structured fields of a statement
(kind, path, original text), never with hand-written answers: the expected statements are
whatever the published dossiers hold at evaluation time. Rankings are computed in memory
from `published_claims()`; the full-text side runs the index expression on literal arrays,
so the evaluation needs neither the index tables nor any write. See
docs/engineering/EVIDENCE_SEARCH.md.
"""

from django.db import connection

from property_platform.modules.catalog.models import Project

from . import embeddings
from .claims import query_terms
from .index import MAX_RESULTS, VECTOR_SQL, fusion_scores, passage_text, published_claims

# (query, language, kind, path prefix, text fragment that must appear; "" = any)
CASES = (
    ("swimming pool", "en", "amenity", "amenity:swimming_pool", ""),
    ("piscine", "fr", "amenity", "amenity:swimming_pool", ""),
    ("مسبح", "ar", "amenity", "amenity:swimming_pool", ""),
    ("游泳池", "zh", "amenity", "amenity:swimming_pool", ""),
    ("gym", "en", "amenity", "amenity:gym", ""),
    ("salle de sport", "fr", "amenity", "amenity:gym", ""),
    ("penthouse", "en", "typologies", "", "Penthouse"),
    ("studio", "en", "typologies", "", "Studio"),
    ("appartements de trois chambres", "fr", "typologies", "", "ThreeBedroom"),
    ("شقق بثلاث غرف", "ar", "typologies", "", "ThreeBedroom"),
    ("villa", "en", "typologies", "", "VILLA"),
    ("handover date", "en", "handover", "", ""),
    ("date de livraison", "fr", "handover", "", ""),
    ("completed", "en", "declared_progress", "", "Completed"),
    ("under construction", "en", "declared_progress", "", "Under Construction"),
    ("项目是否已经完工", "zh", "declared_progress", "", "Completed"),
    ("registration number", "en", "registration", "", ""),
    ("numéro d'enregistrement", "fr", "registration", "", ""),
    ("number of units", "en", "programme_total", "", ""),
    ("nombre de logements", "fr", "programme_total", "", ""),
    ("tower 2", "en", "component_of", "", "Tower 2"),
)
MODES = ("text", "semantic", "hybrid")


def _relevant(claim, kind, path, fragment):
    return (
        claim["kind"] == kind
        and claim["path"].startswith(path)
        and fragment.casefold() in claim["text"].casefold()
    )


def _text_ranking(query, claims):
    terms = query_terms(query)
    if not terms:
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT ord, ts_rank_cd({VECTOR_SQL}, to_tsquery('simple', %s)) "
            "FROM unnest(%s::text[], %s::text[]) WITH ORDINALITY "
            "AS t(search_text, project_terms, ord) "
            f"WHERE {VECTOR_SQL} @@ to_tsquery('simple', %s)",
            [
                terms,
                [claim["search_text"] for claim in claims],
                [claim["project_terms"] for claim in claims],
                terms,
            ],
        )
        ranked = [(rank, claims[ordinal - 1]) for ordinal, rank in cursor.fetchall()]
    # Same order as `search_claims`.
    ranked.sort(key=lambda pair: (-pair[0], *_order(pair[1])))
    return [claim["claim_key"] for _, claim in ranked]


def _semantic_ranking(query, claims, vectors):
    [vector] = embeddings.embed([" ".join(query.split())], role="query")
    scored = sorted(
        ((embeddings.similarity(vector, vectors[claim["claim_key"]]), claim) for claim in claims),
        key=lambda pair: (-pair[0], *_order(pair[1])),
    )
    return [claim["claim_key"] for _, claim in scored]


def _order(claim):
    return (claim["slug"], claim["kind"], claim["path"], claim["claim_key"])


def evaluate(modes=MODES, k=10):
    """Per case and mode: relevant statements, how many are in the first k, first rank."""
    slugs = dict(Project.objects.values_list("id", "slug"))
    names = dict(Project.objects.values_list("id", "name"))
    claims = [
        {**claim, "slug": slugs[claim["project_id"]]} for claim in published_claims().values()
    ]
    claims.sort(key=_order)
    vectors, semantic = {}, False
    if {"semantic", "hybrid"} & set(modes) and embeddings.configured():
        try:
            embeddings.check_model()
            passages = [passage_text(names[c["project_id"]], c["text"]) for c in claims]
            computed = embeddings.embed(passages, role="passage")
            vectors = {c["claim_key"]: v for c, v in zip(claims, computed, strict=True)}
            semantic = True
        except embeddings.EmbeddingsUnavailable:
            semantic = False
    by_key = {claim["claim_key"]: claim for claim in claims}
    rows = []
    for query, language, kind, path, fragment in CASES:
        relevant = {c["claim_key"] for c in claims if _relevant(c, kind, path, fragment)}
        rankings = {"text": _text_ranking(query, claims)}
        if semantic:
            rankings["semantic"] = _semantic_ranking(query, claims, vectors)
            scores = fusion_scores(
                rankings["text"][:MAX_RESULTS], rankings["semantic"][:MAX_RESULTS]
            )
            rankings["hybrid"] = sorted(
                scores, key=lambda key: (-scores[key], *_order(by_key[key]))
            )
        for mode in modes:
            if mode not in rankings:
                continue
            ranking = rankings[mode]
            first = next((i for i, key in enumerate(ranking, 1) if key in relevant), None)
            rows.append(
                {
                    "query": query,
                    "language": language,
                    "mode": mode,
                    "relevant": len(relevant),
                    "answered": len(ranking),
                    f"relevant_in_top_{k}": len(relevant & set(ranking[:k])),
                    "first_relevant_rank": first,
                }
            )
    return {"statements": len(claims), "semantic": semantic, "cases": rows}
