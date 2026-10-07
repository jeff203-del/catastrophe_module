"""Local GeoTIFF metadata, raster-value summaries, and lightweight map previews.

The interpreter supports georeferenced, north-up GeoTIFFs using standard
ModelPixelScale/ModelTiepoint tags in EPSG:4326. It rejects unsupported CRS or
missing georeferencing instead of guessing coordinates.
"""
from __future__ import annotations
from io import BytesIO
import numpy as np
from PIL import Image
from ..config import KENYA_BOUNDS


def _epsg_from_keys(keys):
    """Return EPSG from the GeoKeyDirectory tag, if available."""
    if not keys or len(keys) < 4:
        return None
    number = int(keys[3])
    for index in range(number):
        offset = 4 + index * 4
        if offset + 3 >= len(keys):
            break
        key_id, location, count, value = map(int, keys[offset:offset + 4])
        if key_id in (2048, 3072) and location == 0 and count == 1:
            return value
    return None


def inspect_geotiff(uploaded_file):
    """Read a georeferenced TIFF locally and return metadata plus a PNG overlay.

    Raster values are never sent to an external service. Display resampling is
    capped at 900 px per side. The map overlay uses a red palette and transparent
    NoData cells. Only EPSG:4326 north-up rasters are currently overlaid.
    """
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("The uploaded TIFF is empty")
    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("GeoTIFF exceeds the 100 MB interactive preview limit")
    try:
        source = Image.open(BytesIO(raw))
        tags = source.tag_v2
        width, height = source.size
        if width * height > 30_000_000:
            raise ValueError("GeoTIFF exceeds the 30-million-pixel interactive preview limit")
        epsg = _epsg_from_keys(tags.get(34735))
        if epsg != 4326:
            raise ValueError(f"Unsupported or missing GeoTIFF CRS (EPSG:{epsg or 'unknown'}). Map interpretation currently requires EPSG:4326.")
        scale = tags.get(33550)
        tiepoints = tags.get(33922)
        if not scale or len(scale) < 2 or not tiepoints or len(tiepoints) < 6:
            raise ValueError("GeoTIFF is missing ModelPixelScale or ModelTiepoint georeferencing tags")
        scale_x, scale_y = abs(float(scale[0])), abs(float(scale[1]))
        raster_i, raster_j, _, model_x, model_y, _ = map(float, tiepoints[:6])
        west = model_x - raster_i * scale_x
        north = model_y + raster_j * scale_y
        east = west + width * scale_x
        south = north - height * scale_y
        bounds = [west, south, east, north]
        if not all(np.isfinite(bounds)) or west >= east or south >= north:
            raise ValueError("GeoTIFF has invalid pixel scale or georeferenced bounds")
        overlaps_kenya = (east >= KENYA_BOUNDS["lon_min"] and west <= KENYA_BOUNDS["lon_max"]
                          and north >= KENYA_BOUNDS["lat_min"] and south <= KENYA_BOUNDS["lat_max"])
        data = np.asarray(source)
        if data.ndim == 3:
            data = data[..., 0]
        data = data.astype("float32", copy=False)
        nodata_tag = tags.get(42113)
        try:
            nodata = float(nodata_tag.decode("ascii").strip("<>\x00 ") if isinstance(nodata_tag, bytes) else nodata_tag) if nodata_tag is not None else None
        except (TypeError, ValueError):
            nodata = str(nodata_tag)
        valid_mask = np.isfinite(data)
        if isinstance(nodata, float):
            valid_mask &= data != nodata
        valid = data[valid_mask]
        if valid.size == 0:
            raise ValueError("GeoTIFF's first band contains no valid pixels")
        low, high = map(float, np.percentile(valid, [2, 98]))
        if high <= low:
            high = low + 1.0
        preview = Image.fromarray(data, mode="F")
        preview.thumbnail((900, 900), Image.Resampling.BILINEAR)
        values = np.asarray(preview, dtype="float32")
        if values.shape != valid_mask.shape:
            mask_preview = Image.fromarray(valid_mask.astype("uint8") * 255, mode="L")
            mask_preview.thumbnail((900, 900), Image.Resampling.NEAREST)
            preview_mask = np.asarray(mask_preview) > 0
        else:
            preview_mask = valid_mask
        normalized = np.clip((np.where(np.isfinite(values), values, low) - low) / (high - low), 0, 1)
        start = np.array([247, 247, 250], dtype="float32")
        end = np.array([214, 40, 40], dtype="float32")
        rgb = (start + normalized[..., None] * (end - start)).astype("uint8")
        alpha = np.where(preview_mask, 55 + normalized * 175, 0).astype("uint8")
        png = BytesIO()
        Image.fromarray(np.dstack((rgb, alpha)), mode="RGBA").save(png, format="PNG", optimize=True)
        return {
            "filename": getattr(uploaded_file, "name", "uploaded.tif"),
            "width": int(width), "height": int(height), "bands": int(len(source.getbands())),
            "data_type": source.mode, "crs": f"EPSG:{epsg}", "nodata": nodata,
            "min": float(np.min(valid)), "max": float(np.max(valid)), "mean": float(np.mean(valid)),
            "valid_pixel_count": int(valid.size), "bounds_wgs84": bounds,
            "resolution_native": [scale_x, scale_y], "overlaps_kenya": bool(overlaps_kenya), "png": png.getvalue(),
        }
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"Could not decode this TIFF/GeoTIFF: {exc}") from exc
