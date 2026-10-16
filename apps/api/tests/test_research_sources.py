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


def test_publisher_embed_requires_matching_project_not_the_sales_office():
    url = "https://www.saasproperties.com/en/properties/abu-dhabi/reem-nine/"
    payload = b'<iframe src="https://www.google.com/maps/embed?pb=!2d54.408!3d24.496!2sReem%20Nine%20by%20SAAS!5e0"></iframe>'
    assert project_marker(payload, url, "Reem Nine") is None
    payload = payload.replace(b"!5e0", b"!8m2!3d24.49618!4d54.41036!5e0")
    point = project_marker(payload, url, "Reem Nine")
    assert point["lon"] == 54.41036 and point["lat"] == 24.49618
    assert point["method"] == "publisher_embedded_pin"
    assert project_marker(payload, url, "One Reem Island") is None
    assert (
        project_marker(payload.replace(b"www.google.com", b"untrusted.example"), url, "Reem Nine")
        is None
    )


def test_bloom_position_and_object_marker_ignore_surrounding_attractions():
    payload = b'<div id="map_canvas" data-location="24.5238499,54.4324551"></div>'
    assert (
        project_marker(
            payload, "https://bloomholding.com/what-we-do/properties/park-view", "Park View"
        )["lat"]
        == 24.5238499
    )
    markers = [
        {"type": "object", "lat": 24.489, "lng": 54.409, "label": "A1LA RESIDENCE"},
        {"type": "attraction", "lat": 24.5, "lng": 54.4, "label": "A1LA RESIDENCE"},
    ]
    payload = f"<div data-markers='{json.dumps(markers)}'></div>".encode()
    assert (
        project_marker(payload, "https://object-1.com/project/a1la-residence/", "A1LA Residence")[
            "lon"
        ]
        == 54.409
    )
