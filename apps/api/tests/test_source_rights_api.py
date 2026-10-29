from django.test import override_settings

from property_platform.modules.evidence.source_rights import source_rights


def test_source_rights_list_the_reviewed_registry(client):
    with override_settings(DEBUG=True, PROPERTY_PLATFORM_PARCEL_PREVIEW=True):
        response = client.get("/api/v1/preview/source-rights")
    assert response.status_code == 200
    items = response.json()["items"]
    registry = source_rights()
    assert [item["host"] for item in items] == [row["host"] for row in registry]
    for item, row in zip(items, registry, strict=True):
        # Who reviewed and why stay in the registry; readers get rights and links.
        assert "reviewed_by" not in item and "basis" not in item
        assert item["publisher"] == row["publisher"]
        assert item["licence"] == row["licence"]
        assert item["collection"] == row["collection"]
        assert item["publication"] == row["publication"]
        assert item["reviewed_on"] == row["reviewed_on"]
        assert item["licence_url"] == (row["licence_url"] or None)
        assert item["terms_url"] == (row["terms_url"] or None)
        assert item["attribution"] == (row["attribution"] or None)


STAMP = "2026-10-20T00:00:00Z"
PSI = "https://psinv.net/en/projects/abu-dhabi/al-reem-island/renad-tower-1"
OSM = "https://www.openstreetmap.org/"
SDI = "https://arcgis.sdi.abudhabi.ae/agshost/rest/services/Hosted/Plots/FeatureServer/0"


def _provenance(url, **extra):
    return {
        "name": "Source",
        "url": url,
        "retrieved_at": STAMP,
        "published_at": None,
        "ingested_at": STAMP,
        **extra,
    }


def test_every_cited_source_states_the_rights_of_its_site(enforce_rights):
    from property_platform.api.accessibility import WalkingResponse
    from property_platform.api.evidence_search import EvidenceSearchSourceResponse
    from property_platform.api.parcels import FieldHistory, Provenance, ResearchReferenceResponse
    from property_platform.api.projects import ProjectSourceResponse

    enforce_rights(collection=False, publication=False)
    detail = Provenance.model_validate(_provenance(PSI))
    assert (detail.rights.licence, detail.rights.publication) == ("proprietary", "none")
    # Shown only because publication is not enforced (A22).
    assert detail.rights.shown_beyond_terms
    history = FieldHistory.model_validate({"url": OSM, "retrieved_at": STAMP, "ingested_at": STAMP})
    assert history.rights.licence == "ODbL-1.0"
    reference = ResearchReferenceResponse.model_validate(
        {
            "label": "Forum",
            "title": "Thread",
            "source_kind": "forum",
            "available": True,
            "place_id": None,
            "url": "https://www.reddit.com/r/AbuDhabi/comments/x/",
            "retrieved_at": STAMP,
            "published_at": None,
        }
    )
    assert reference.rights.publication == "none"
    search = EvidenceSearchSourceResponse.model_validate(
        {
            "url": PSI,
            "name": "PSI",
            "kind": "broker",
            "content_sha256": None,
            "evidence_pointer": "",
            "retrieved_at": None,
        }
    )
    assert search.rights.licence == "proprietary"
    walking = WalkingResponse.model_validate(
        {
            "collection": {"type": "FeatureCollection", "features": []},
            "ingested_at": STAMP,
            "graph_id": "1",
            "graph_fetched_at": STAMP,
            "source_url": "https://download.geofabrik.de/asia/gcc-states-261019.osm.pbf",
            "historical": False,
        }
    )
    assert walking.rights.licence == "ODbL-1.0"
    # A project source keeps the rights its read computed, else gets them from its page.
    source = ProjectSourceResponse.model_validate(
        {"url": PSI, "name": "PSI", "retrieved_at": STAMP, "published_at": None, "language": "en"}
    )
    assert source.rights.publication == "none"


def test_map_lists_state_each_cited_site_once():
    from property_platform.api.parcels import Collection, MapCollection

    parcel = {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": []},
        "properties": {
            "code": "C1",
            "community": "Reem",
            "land_use": "",
            "construction_status": "",
            "category": "",
            "source_url": SDI,
            "source_name": "AD-SDI",
        },
    }
    parcels = Collection.model_validate(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    **parcel,
                    "id": f"00000000-0000-0000-0000-00000000000{n}",
                    "properties": {
                        **parcel["properties"],
                        "id": f"00000000-0000-0000-0000-00000000000{n}",
                    },
                }
                for n in (1, 2, 3)
            ],
            "truncated": False,
            "classification_version": "test",
        }
    )
    assert [(source.url, source.name) for source in parcels.sources] == [(SDI, "AD-SDI")]
    assert parcels.sources[0].rights.licence == "unknown"
    place = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [54.39, 24.5]},
        "properties": {
            "id": "00000000-0000-0000-0000-000000000009",
            "name": "Park",
            "name_ar": "",
            "kind": "park",
            "source": _provenance(
                OSM,
                reliability="community",
                acquisition_method="live",
                timestamp_basis="collector_clock",
            ),
        },
    }
    places = MapCollection.model_validate(
        {
            "type": "FeatureCollection",
            "features": [{**place, "id": place["properties"]["id"]}],
            "truncated": False,
        }
    )
    assert [source.rights.licence for source in places.sources] == ["ODbL-1.0"]
    # Each feature keeps its provenance without repeating the rights.
    assert "rights" not in places.features[0].properties.source.model_dump()
