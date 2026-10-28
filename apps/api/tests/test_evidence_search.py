"""Statements a published dossier makes, as the evidence search index reads them (E01)."""

from property_platform.modules.evidence.search.claims import (
    claims_from_dossier,
    normalize,
    project_terms,
    query_terms,
)

SOURCE = {
    "url": "https://example.test/project",
    "name": "Developer",
    "kind": "developer",
    "content_sha256": "a" * 64,
    "evidence_pointer": "JSON:data.completionDate",
    "retrieved_at": "2026-10-20T10:00:00+00:00",
    "language": "en",
    "historical": False,
}


def dossier(**values):
    return {
        "slug": "sample-tower",
        "name": "Sample Tower",
        "language": "en",
        "developer": {"name": "Sample Developer"},
        **values,
    }


def test_normalize_folds_accents_case_and_arabic_spellings():
    assert normalize("Résidence ÉTÉ") == "residence ete"
    assert normalize("أبراج الرِّيم") == normalize("ابراج الريم")
    assert normalize("مدينة") == normalize("مدينه")
    assert normalize("swimming_pool 2023/302023") == "swimming pool 2023 302023"


def test_normalize_splits_han_and_kana_into_single_characters():
    assert normalize("东京タワー") == "东 京 タ ワ ー"


def test_query_terms_are_prefixes_of_normalized_words_only():
    assert query_terms("Gate & (Arc) | !tower") == "gate:* & arc:* & tower:*"
    assert query_terms("  ") == ""


def test_statements_keep_the_original_text_and_their_evidence():
    rows = claims_from_dossier(
        dossier(
            handover={"original_text": "2029-08-31", "source": SOURCE},
            programme_total={"original_text": "totalUnits: 78", "source": SOURCE},
        )
    )
    assert [(row["kind"], row["text"]) for row in rows] == [
        ("handover", "2029-08-31"),
        ("programme_total", "totalUnits: 78"),
    ]
    assert rows[0]["source_url"] == SOURCE["url"]
    assert rows[0]["evidence_pointer"] == SOURCE["evidence_pointer"]
    assert rows[0]["content_sha256"] == SOURCE["content_sha256"]


def test_a_statement_without_current_evidence_is_never_indexed():
    rows = claims_from_dossier(
        dossier(
            summary="Sea views",
            summary_source=None,
            handover={"original_text": "2028", "source": {**SOURCE, "historical": True}},
            programme_total={"original_text": "", "source": SOURCE},
        )
    )
    assert rows == []


def test_typologies_read_from_one_text_are_one_statement():
    text = '{"unitTypes": ["Apartment", "Penthouse"]}'
    rows = claims_from_dossier(
        dossier(
            typologies=[
                {
                    "property_type": "apartment",
                    "bedrooms": None,
                    "original_text": text,
                    "source": SOURCE,
                },
                {
                    "property_type": "penthouse",
                    "bedrooms": 4,
                    "original_text": text,
                    "source": SOURCE,
                },
            ]
        )
    )
    assert len(rows) == 1
    assert rows[0]["text"] == text
    assert {"apartment", "penthouse", "4"} <= set(rows[0]["search_text"].split())


def test_claim_keys_are_stable_and_change_with_the_evidence():
    first = claims_from_dossier(dossier(handover={"original_text": "2029", "source": SOURCE}))
    again = claims_from_dossier(dossier(handover={"original_text": "2029", "source": SOURCE}))
    reread = claims_from_dossier(
        dossier(
            handover={"original_text": "2029", "source": {**SOURCE, "content_sha256": "b" * 64}}
        )
    )
    assert first[0]["claim_key"] == again[0]["claim_key"]
    assert first[0]["claim_key"] != reread[0]["claim_key"]


def test_register_values_are_joined_with_their_published_names():
    rows = claims_from_dossier(
        dossier(
            verification={
                "latest_reading": {
                    "registration_number": "2023/302023",
                    "permit_number": "4158393",
                    "register_status": "Completed",
                    "sold_original": "30.17%",
                    "source": SOURCE,
                }
            }
        )
    )
    assert rows[0]["kind"] == "registration"
    assert rows[0]["text"] == (
        "registration_number: 2023/302023; permit_number: 4158393; "
        "register_status: Completed; sold: 30.17%"
    )


def test_project_terms_carry_the_name_developer_and_slug():
    assert project_terms(dossier()) == "sample tower sample developer sample tower"
