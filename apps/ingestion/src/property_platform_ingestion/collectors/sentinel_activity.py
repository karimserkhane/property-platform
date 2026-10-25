"""Sentinel-2 construction activity signal: scene selection and the pure change index.

The index compares two dated, cloud-masked Sentinel-2 L2A windows of one parcel. It is a
signal of ground change, never a construction progress percentage: 10 m pixels do not
measure floors, and a change can be earthworks, storage or demolition. Raster reading
stays in ingestion; these functions take arrays already aligned on the 10 m grid.
See docs/engineering/CONSTRUCTION_ACTIVITY.md.
"""

import re
from datetime import UTC, datetime

import numpy as np

METHOD_VERSION = "sentinel-activity-v1"
COLLECTION = "sentinel-2-l2a"
ASSET_HOST = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/"
# 10 m Earth Search asset keys (B02, B03, B04, B08) and the 20 m scene classification.
BANDS = ("blue", "green", "red", "nir")
CLASSIFICATION = "scl"
# SCL classes kept: 4 vegetation, 5 not vegetated, 6 water, 7 unclassified. Rejected:
# 0 no data, 1 saturated, 2 dark area, 3 cloud shadow, 8-10 clouds and cirrus, 11 snow.
CLEAR_CLASSES = (4, 5, 6, 7)
MAX_SCENE_CLOUD = 20.0
# Mean reflectance difference above which a 10 m pixel counts as changed.
CHANGE_THRESHOLD = 0.05
MIN_CLEAR_PIXELS = 20
MIN_CLEAR_SHARE = 0.6
# Levels of the changed-pixel share; heuristic thresholds of method v1, shown as levels.
LEVELS = ((0.1, "low"), (0.3, "moderate"), (1.0, "high"))

_SCENE_ID = re.compile(r"^S2[ABC]_\d{2}[A-Z]{3}_\d{8}_\d+_L2A$")


class SceneError(ValueError):
    """A STAC item does not match the reviewed Sentinel-2 L2A shape."""


def scene_record(feature):
    """Return the reviewed fields of one Earth Search item, or raise SceneError."""
    try:
        identity = feature["id"]
        properties = feature["properties"]
        acquired = datetime.fromisoformat(properties["datetime"].replace("Z", "+00:00"))
        cloud = float(properties["eo:cloud_cover"])
        tile = properties["grid:code"]
        assets = {key: feature["assets"][key] for key in (*BANDS, CLASSIFICATION)}
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise SceneError("Incomplete Sentinel-2 item") from exc
    if (
        feature.get("collection") != COLLECTION
        or not isinstance(identity, str)
        or not _SCENE_ID.match(identity)
        or acquired.tzinfo is None
        or not 0 <= cloud <= 100
        or not isinstance(tile, str)
        or not tile.startswith("MGRS-")
    ):
        raise SceneError("Unexpected Sentinel-2 item")
    bands = {}
    for key, asset in assets.items():
        href = asset.get("href") if isinstance(asset, dict) else None
        if not isinstance(href, str) or not href.startswith(ASSET_HOST) or ".." in href:
            raise SceneError("Unexpected Sentinel-2 asset host")
        scale, offset = 1.0, 0.0
        if key != CLASSIFICATION:
            band = (asset.get("raster:bands") or [{}])[0]
            scale, offset = float(band.get("scale", 1.0)), float(band.get("offset", 0.0))
            if not 0 < scale <= 1 or not -1 <= offset <= 0:
                raise SceneError("Unexpected Sentinel-2 reflectance scaling")
        bands[key] = {"href": href, "scale": scale, "offset": offset}
    return {
        "scene_id": identity,
        "acquired_at": acquired.astimezone(UTC),
        "cloud_cover": cloud,
        "tile": tile,
        "assets": bands,
    }


def select_scenes(features, *, max_cloud=MAX_SCENE_CLOUD):
    """Keep the least cloudy scene per MGRS tile and calendar month, oldest first.

    One scene per month bounds the raster reads and avoids comparing two passes a few
    days apart. Scenes above the cloud budget are never selected as a fallback.
    """
    chosen = {}
    for feature in features:
        record = scene_record(feature)
        if record["cloud_cover"] > max_cloud:
            continue
        month = record["acquired_at"].strftime("%Y-%m")
        key = (record["tile"], month)
        current = chosen.get(key)
        if current is None or (record["cloud_cover"], record["scene_id"]) < (
            current["cloud_cover"],
            current["scene_id"],
        ):
            chosen[key] = record
    return sorted(chosen.values(), key=lambda row: (row["tile"], row["acquired_at"]))


def reflectance(values, *, scale, offset):
    """Convert L2A digital numbers to reflectance; 0 is the no-data value."""
    values = np.asarray(values)
    output = values.astype(np.float64) * scale + offset
    output[values == 0] = np.nan
    return output


def change_signal(before, after, parcel):
    """Compare two windows of one parcel; return counts and a level, never a progress.

    ``before`` and ``after`` map each band of BANDS to reflectance and ``scl`` to the
    scene classification, all on the same grid as the boolean ``parcel`` mask.
    """
    parcel = np.asarray(parcel, dtype=bool)
    shapes = {np.shape(window[key]) for window in (before, after) for key in (*BANDS, "scl")}
    if shapes != {parcel.shape}:
        raise ValueError("Windows and parcel mask must share one grid")
    parcel_pixels = int(parcel.sum())
    if parcel_pixels == 0:
        raise ValueError("Parcel does not cover any 10 m pixel")
    clear = parcel.copy()
    for window in (before, after):
        clear &= np.isin(window["scl"], CLEAR_CLASSES)
        for band in BANDS:
            clear &= np.isfinite(window[band])
    clear_pixels = int(clear.sum())
    result = {
        "method_version": METHOD_VERSION,
        "parcel_pixels": parcel_pixels,
        "clear_pixels": clear_pixels,
        "changed_pixels": None,
        "changed_share": None,
        "median_difference": None,
        "level": None,
        "status": "insufficient_clear_pixels",
    }
    if clear_pixels < MIN_CLEAR_PIXELS or clear_pixels < MIN_CLEAR_SHARE * parcel_pixels:
        return result
    difference = np.mean(
        [np.abs(after[band][clear] - before[band][clear]) for band in BANDS], axis=0
    )
    changed = int((difference > CHANGE_THRESHOLD).sum())
    share = changed / clear_pixels
    result.update(
        changed_pixels=changed,
        changed_share=round(share, 4),
        median_difference=round(float(np.median(difference)), 4),
        level=next(level for limit, level in LEVELS if share <= limit),
        status="measured",
    )
    return result
