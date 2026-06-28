"""
config.py — Herschel Island / Qikiqtaruk site configuration.
See config.py in the shingle-point-dashboard repo for full documentation
of each field — this file follows the identical structure.
"""

import dashboard_lib as lib

SITE_DISPLAY_NAME = "Qikiqtaruk Herschel Island"
LAT = 69.590
LON = -139.099
TZ_NAME = "America/Inuvik"

_HALF_WIDTH_M = 150_000
_MODIS_OVERSIZE_HALF_WIDTH_M = _HALF_WIDTH_M * lib.MODIS_OVERSIZE_FACTOR

# Computed via lib.compute_3413_center(LAT, LON).
MODIS_CENTER_X, MODIS_CENTER_Y = -2230848, 152544

MODIS_BBOX_3413 = (
    f"{MODIS_CENTER_X - _MODIS_OVERSIZE_HALF_WIDTH_M:.0f},{MODIS_CENTER_Y - _MODIS_OVERSIZE_HALF_WIDTH_M:.0f},"
    f"{MODIS_CENTER_X + _MODIS_OVERSIZE_HALF_WIDTH_M:.0f},{MODIS_CENTER_Y + _MODIS_OVERSIZE_HALF_WIDTH_M:.0f}"
)

# Empirically verified (this is the original, longest-running site, and
# this value has been confirmed against real rendered images).
MODIS_ROTATION_DEG = 86.09

# Herschel Island IS genuinely zone 7 (verified via lib.compute_utm_zone(LON))
# — unlike Shingle Point, which is zone 8 despite being nearby. Do not
# assume any future site shares either of these without checking.
UTM_ZONE = 7
UTM_EPSG = "32607"
UTM_CENTER_X, UTM_CENTER_Y = lib.latlon_to_utm(LAT, LON, zone=UTM_ZONE)

MAP_POINTS = [
    (69.568861, -138.911754, SITE_DISPLAY_NAME, -28),
    (68.933333, -137.2, "Shingle Point", -10),
    (68.226653, -135.003294, "Aklavik", -10),
    (68.360741, -133.723022, "Inuvik", -10, -90),
]

MAP_REFERENCE_LINES = [
    (60.0, -141.0, 69.65, -141.0, "Yukon/Alaska border"),
]

COASTLINE_GEOJSON_PATH = "coastline_data.geojson"

TIDE_STATION_CODE = "06525"
TIDE_STATION_NAME = "Herschel Island"

MARINE_ZONE_ID = "16000"
MARINE_ZONE_NAME = "Yukon Coast"

WATER_LEVEL_YEARLY_MEAN = -0.2668  # re-verify independently for this site if it drifts from Shingle Point's

# Herschel Island has no hydrometric river gauge nearby (unlike Shingle
# Point's Napoiak Channel station) — empty list, that section simply
# doesn't appear on this site's page.
HYDROMETRIC_STATIONS = []

LOGO_URL = "https://www.awi.de/_assets/978631966794c5093250775de182779d/Images/AWI/awi_logo.svg"
INSTITUTION_TEXT = (
    "This dashboard is provided by the Alfred Wegener Institute Helmholtz Centre "
    "for Polar and Marine Research."
)
