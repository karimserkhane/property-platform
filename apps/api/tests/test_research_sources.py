import json

from property_platform.modules.evidence.research_sources import project_marker


def test_only_project_jsonld_with_matching_name_and_url_becomes_declared_point():
    url = "https://jre.ae/projects/example-tower"
    record = {
        "@type": "RealEstateListing",
        "name": "Example Tower",
        "url": url,
        "geo": {"@type": "GeoCoordinates", "latitude": 24.5, "longitude": 54.4},
    }
    payload = f'<script type="application/ld+json">{json.dumps(record)}</script>'.encode()
    assert (
        project_marker(payload, url, "Example Tower | Broker")["method"]
        == "declared_jsonld_project"
    )
    assert project_marker(payload, url, "Another Project | Broker") is None
    assert (
        project_marker(payload, "https://unknown.example/projects/example-tower", "Example Tower")
        is None
    )
    record["@type"] = "Organization"
    payload = f'<script type="application/ld+json">{json.dumps(record)}</script>'.encode()
    assert project_marker(payload, url, "Example Tower") is None


def test_copied_coordinates_with_a_different_project_name_are_rejected():
    payload = (
        b'<div class="marker" data-lat="24.509268" data-lng="54.40437">'
        b"<p>Marlin 2 by Reportage, Walking beach Reem</p></div>"
    )
    url = "https://reportagegroup.com/projects/residential-apartments/marlin/"
    assert project_marker(payload, url, "Marlin 1 - Reportage") is None
    assert project_marker(payload, url, "Marlin 2 - Reportage")["name"] == "Marlin 2"


def test_multiple_conflicting_project_points_remain_unlocated():
    url = "https://rendr.ae/projects/example"
    records = [
        {
            "@type": "ApartmentComplex",
            "name": "Example",
            "geo": {"@type": "GeoCoordinates", "latitude": 24.5, "longitude": lon},
        }
        for lon in [54.4, 54.41]
    ]
    payload = f'<script type="application/ld+json">{json.dumps(records)}</script>'.encode()
    assert project_marker(payload, url, "Example") is None
