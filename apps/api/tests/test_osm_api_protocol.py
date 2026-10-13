import pytest

from property_platform.modules.evidence.onwani import SourceError
from property_platform.modules.evidence.osm_api_protocol import boxes, decode

XML = b"""<osm version="0.6">
<node id="1" lat="24.54" lon="54.41" version="1" timestamp="2026-01-01T00:00:00Z" />
<node id="2" lat="24.54" lon="54.42" version="1" timestamp="2026-01-01T00:00:00Z" />
<node id="3" lat="24.55" lon="54.41" version="1" timestamp="2026-01-01T00:00:00Z" />
<way id="10" version="2" timestamp="2026-02-01T00:00:00Z">
<nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="1"/>
<tag k="building" v="apartments"/><tag k="name" v="Test residence"/></way></osm>"""


def test_xml_preserves_identity_geometry_and_original_edit_date():
    row = decode(XML)["elements"][0]
    assert row["type"] == "way" and row["id"] == 10 and row["version"] == 2
    assert row["timestamp"] == "2026-02-01T00:00:00Z"
    assert row["geometry"][0] == row["geometry"][-1]
    assert len(boxes("saadiyat-island")) == 4
    with pytest.raises(ValueError):
        boxes("al-reem-island")


@pytest.mark.parametrize(
    "payload",
    [
        b'<!DOCTYPE osm [<!ENTITY x "bad">]><osm version="0.6"/>',
        XML.replace(b'<nd ref="2"/>', b'<nd ref="99"/>'),
    ],
)
def test_xml_rejects_entities_and_missing_node_references(payload):
    with pytest.raises(SourceError):
        decode(payload)


def test_utf16_cannot_bypass_the_entity_guard():
    payload = '<!DOCTYPE osm [<!ENTITY x "bad">]><osm version="0.6"/>'.encode("utf-16")
    with pytest.raises(SourceError):
        decode(payload)
