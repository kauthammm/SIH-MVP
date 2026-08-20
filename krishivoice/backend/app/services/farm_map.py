"""Farm map + segment data for profile (CSV parcels and custom FL lands)."""

from __future__ import annotations



from typing import Any



from app.services import csv_store

from app.services.profile_store import (

    custom_land_as_parcel,

    get_custom_land,

    is_custom_land,

    load_profile,

)





def get_farm_map_data(farmer_id: str, parcel_id: str) -> dict[str, Any]:

    prof = load_profile(farmer_id)

    custom = prof.get("parcels", {}).get(parcel_id, {})



    if is_custom_land(farmer_id, parcel_id):

        base = custom_land_as_parcel(farmer_id, parcel_id) or {}

        parcel = base

    else:

        parcel = csv_store.get_parcel(parcel_id)

        if not parcel or parcel.get("farmer_id") != farmer_id:

            if get_custom_land(farmer_id, parcel_id):

                base = custom_land_as_parcel(farmer_id, parcel_id) or {}

                parcel = base

            else:

                return {}



    segments = custom.get("segments") or _default_segments(parcel, custom)



    lat = custom.get("latitude", parcel.get("latitude"))

    lon = custom.get("longitude", parcel.get("longitude"))

    boundary = custom.get("boundary")

    area = custom.get("area", parcel.get("area", 0))

    if boundary and not custom.get("area"):

        from app.services.geo_utils import polygon_area_ha

        area = polygon_area_ha(boundary)



    return {

        "farmer_id": farmer_id,

        "parcel_id": parcel_id,

        "land_name": custom.get("land_name") or parcel.get("land_name") or parcel.get("village"),

        "is_custom_land": bool(custom.get("is_custom_land") or parcel_id.startswith("FL")),

        "district": custom.get("district", parcel.get("district")),

        "village": custom.get("village", parcel.get("village")),

        "taluk": custom.get("taluk", parcel.get("taluk")),

        "centroid": {"lat": float(lat), "lng": float(lon)},

        "area_ha": float(area or 0),

        "boundary": boundary,

        "segments": segments,

        "crop": custom.get("crop"),

        "growth_stage": custom.get("growth_stage"),

        "soil": custom.get("soil"),

        "land_type": custom.get("land_type"),

        "irrigation_source": custom.get("irrigation_source"),

        "land_slope": custom.get("land_slope"),

        "drainage": custom.get("drainage"),

        "water_table": custom.get("water_table"),

        "soil_texture": custom.get("soil_texture"),

        "field_condition": custom.get("field_condition"),

    }





def _default_segments(parcel: dict, custom: dict) -> list[dict[str, Any]]:

    lat = float(custom.get("latitude", parcel.get("latitude", 10.787)))

    lon = float(custom.get("longitude", parcel.get("longitude", 79.137)))

    return [{

        "segment_id": "S1",

        "name": custom.get("land_name") or "Main field",

        "crop": custom.get("crop", "Rice"),

        "growth_stage": custom.get("growth_stage", "Tillering"),

        "area_ha": float(custom.get("area") or parcel.get("area") or 1),

        "soil_type": (custom.get("soil") or {}).get("soil_type", parcel.get("soil_type", "Clay Loam")),

        "soil_moisture": custom.get("soil_moisture"),

        "soil": custom.get("soil"),

        "latitude": lat,

        "longitude": lon,

        "color": "#40916c",

    }]





def update_farm_segments(farmer_id: str, parcel_id: str, segments: list[dict[str, Any]]) -> dict[str, Any]:

    from app.services.profile_store import update_parcel_custom

    return update_parcel_custom(farmer_id, parcel_id, {"segments": segments})


