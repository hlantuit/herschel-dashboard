
"""
ONE-OFF SCRIPT — run this once (locally, or as a one-time GitHub Actions
manual run) to compute the water level yearly mean for Herschel Island.
 
This value barely changes year to year, so rather than recomputing it on
every dashboard run (which was confirmed, via real test runs, to often
exceed 30+ seconds against the remote THREDDS server — a genuinely
expensive query, not a coding inefficiency), it's computed once here and
the printed result is hardcoded as a constant directly in
dashboard_update.py.
 
Usage:
    pip install xarray netCDF4 numpy --break-system-packages
    python3 compute_yearly_mean_once.py
 
Then copy the printed mean value into dashboard_update.py's
WATER_LEVEL_YEARLY_MEAN constant, and the timestamp comment alongside it
(so it's clear when this was last computed, in case it's ever worth
refreshing — e.g. if you notice the chart's values seem to drift
meaningfully from "typical" over a few years).
"""
import math
from datetime import datetime, timedelta
 
import numpy as np
import xarray as xr
 
LAT = 69.590
LON = -139.099
THREDDS_URL = "https://thredds.met.no/thredds/dodsC/cmems/topaz6/dataset-topaz6-arc-15min-3km-be.ncml"
UNIT_SCALE = 100_000  # this file's x/y coordinates are in units of 100km, not plain meters — confirmed earlier
 
 
def latlon_to_3413(lat_deg, lon_deg):
    """Standard EPSG:3413 polar stereographic forward projection (WGS84)."""
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = 2 * f - f ** 2
    e = math.sqrt(e2)
    lat_ts = math.radians(70)
    lon0 = math.radians(-45)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    t_c = math.tan(math.pi / 4 - lat_ts / 2) / (((1 - e * math.sin(lat_ts)) / (1 + e * math.sin(lat_ts))) ** (e / 2))
    m_c = math.cos(lat_ts) / math.sqrt(1 - e2 * math.sin(lat_ts) ** 2)
    t = math.tan(math.pi / 4 - lat / 2) / (((1 - e * math.sin(lat)) / (1 + e * math.sin(lat))) ** (e / 2))
    rho = a * m_c * (t / t_c)
    x = rho * math.sin(lon - lon0)
    y = -rho * math.cos(lon - lon0)
    return x, y
 
 
def main():
    print("Opening dataset (this can take a while)...")
    ds = xr.open_dataset(THREDDS_URL)
 
    target_x_m, target_y_m = latlon_to_3413(LAT, LON)
    target_x = target_x_m / UNIT_SCALE
    target_y = target_y_m / UNIT_SCALE
 
    print(f"Target point (native units): x={target_x:.3f}, y={target_y:.3f}")
 
    # Same small-neighborhood search as the main script, to land on a
    # genuinely valid (non-land, non-NaN) cell near Herschel Island.
    search_radius = 50_000 / UNIT_SCALE
    x_coords = ds["x"].values
    y_coords = ds["y"].values
    x_ascending = x_coords[0] < x_coords[-1]
    y_ascending = y_coords[0] < y_coords[-1]
    x_slice = slice(target_x - search_radius, target_x + search_radius) if x_ascending \
        else slice(target_x + search_radius, target_x - search_radius)
    y_slice = slice(target_y - search_radius, target_y + search_radius) if y_ascending \
        else slice(target_y + search_radius, target_y - search_radius)
 
    nearby = ds["zos"].sel(x=x_slice, y=y_slice)
 
    now = datetime.utcnow()
    year_start = now - timedelta(days=365)
 
    print("Slicing to the past 365 days (this is the potentially slow step)...")
    nearby_year = nearby.sel(time=slice(year_start, now))
 
    print("Finding a valid grid cell near Herschel Island...")
    has_valid_data = nearby_year.notnull().any(dim="time").values
    xs = nearby_year["x"].values
    ys = nearby_year["y"].values
 
    best_point = None
    best_dist = None
    for yi_idx, yi in enumerate(ys):
        for xi_idx, xi in enumerate(xs):
            if has_valid_data[yi_idx, xi_idx]:
                dist = math.hypot(xi - target_x, yi - target_y)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_point = (xi, yi)
 
    if best_point is None:
        print("ERROR: no valid grid cell found near Herschel Island.")
        return
 
    print(f"Using grid cell at distance {best_dist * UNIT_SCALE:.0f}m from Herschel Island")
    print("Extracting the past year of values at this cell...")
 
    point_series = nearby_year.sel(x=best_point[0], y=best_point[1])
    values = point_series.values.flatten()
    valid_values = values[~np.isnan(values)]
 
    if len(valid_values) == 0:
        print("ERROR: no valid values found in the past-year window.")
        return
 
    yearly_mean = float(np.mean(valid_values))
 
    print("\n" + "=" * 60)
    print(f"RESULT: yearly mean water level = {yearly_mean:.4f} m")
    print(f"(computed from {len(valid_values)} valid 15-minute readings)")
    print(f"Computed at: {now.isoformat()} UTC")
    print("=" * 60)
    print("\nCopy this into dashboard_update.py:")
    print(f'WATER_LEVEL_YEARLY_MEAN = {yearly_mean:.4f}  # computed {now.strftime("%Y-%m-%d")} via compute_yearly_mean_once.py')
 
 
if __name__ == "__main__":
    main()
 
