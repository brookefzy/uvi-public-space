# load projected data
import pandas as pd
import geopandas as gpd
import os
import numpy as np
from shapely.geometry import Point


def get_speed_vector(keepGDF, n=0.5, fps=29.97, globalcrs="EPSG:3857"):
    """This function calculate the speed vector for each track"""
    # Interpolate the missing lat lon for each track_id, frame_id combination
    frame_id_min_max = (
        keepGDF.groupby("track_id")["frame_id"].agg(["min", "max"]).reset_index()
    )

    # Create a new dataframe with all frame_ids for each track
    all_frames = pd.DataFrame(
        [
            {"track_id": row["track_id"], "frame_id": frame_id}
            for track_id, row in frame_id_min_max.iterrows()
            for frame_id in range(row["min"], row["max"] + 1)
        ]
    )

    # Merge with the original dataframe to get the existing lat and lon
    keepGDF = all_frames.merge(
        keepGDF[["track_id", "frame_id", "lat", "lon"]],
        on=["track_id", "frame_id"],
        how="left",
    )

    # Interpolate the missing lat and lon
    keepGDF["lat"] = keepGDF.groupby("track_id")["lat"].apply(
        lambda group: group.interpolate()
    )
    keepGDF["lon"] = keepGDF.groupby("track_id")["lon"].apply(
        lambda group: group.interpolate()
    )
    keepGDF = gpd.GeoDataFrame(
        keepGDF,
        geometry=[Point(x, y) for x, y in zip(keepGDF["lon"], keepGDF["lat"])],
        crs=f"EPSG:4326",
    )
    keepGDF = keepGDF.to_crs(globalcrs)
    testgdf = keepGDF[keepGDF["geometry"].isnull() == False].reset_index(drop=True)
    print(testgdf.shape[0], " remaining after dropping null geometry")
    testgdf = testgdf[
        testgdf["track_id"].map(testgdf["track_id"].value_counts()) > 1
    ].reset_index(drop=True)
    print(testgdf.shape[0], " remaining after dropping track_id with only one frame")

    # remove the outlier - break the track id if the distance is too large
    testgdf_shift = testgdf.copy()
    testgdf_shift["geometry_shift"] = (
        testgdf_shift.sort_values(["frame_id"]).groupby("track_id")["geometry"].shift(1)
    )
    testgdf_shift = testgdf_shift[
        testgdf_shift["geometry_shift"].isnull() == False
    ].reset_index(drop=True)
    testgdf_shift["dist"] = testgdf_shift["geometry_shift"].distance(
        testgdf_shift["geometry"]
    )
    testgdf = testgdf.merge(
        testgdf_shift[["track_id", "frame_id", "dist"]],
        on=["track_id", "frame_id"],
        how="left",
    )

    # calculate individual walking speed at each frame
    # step 1: calculate distance between every n seconds
    shift_inter = int(n * fps)
    keepGDF = testgdf.sort_values(
        [
            "track_id",
            "frame_id",
        ]
    ).reset_index(drop=True)
    keepGDF_copy = keepGDF.copy()
    keepGDF_copy["geometry_shift"] = keepGDF_copy.groupby("track_id")["geometry"].shift(
        shift_inter
    )
    keepGDF_copy[f"move_m_{n}s"] = keepGDF_copy.apply(
        lambda x: x["geometry"].distance(x["geometry_shift"]), axis=1
    )

    keepGDF = keepGDF.merge(
        keepGDF_copy[["track_id", "frame_id", f"move_m_{n}s"]],
        on=["track_id", "frame_id"],
        how="left",
    ).fillna(0)

    keepGDF[f"speed_{n}s"] = keepGDF[f"move_m_{n}s"] / n
    keepGDF[f"speed_{n}s"] = keepGDF.groupby("track_id")[f"speed_{n}s"].fillna(
        method="bfill"
    )
    # calcualte speed_x and speed_y for each person
    keepGDF["x_3857"] = keepGDF["geometry"].x
    keepGDF["y_3857"] = keepGDF["geometry"].y
    keepGDF[f"dist_x_{n}s"] = keepGDF.groupby("track_id")["x_3857"].transform(
        lambda x: x.shift(shift_inter).fillna(method="bfill") - x
    )
    keepGDF[f"dist_y_{n}s"] = keepGDF.groupby("track_id")["y_3857"].transform(
        lambda x: x.shift(shift_inter).fillna(method="bfill") - x
    )
    keepGDF[f"speed_x_{n}s"] = keepGDF[f"dist_x_{n}s"] / n
    keepGDF[f"speed_y_{n}s"] = keepGDF[f"dist_y_{n}s"] / n

    keepGDF["track_id_backup"] = keepGDF["track_id"]
    # keepGDF["track_id_break"] = np.where(keepGDF["dist"] > 1, 1, 0)
    # keepGDF["track_id_update"] = keepGDF["track_id_break"].fillna(0).astype(int)
    # keepGDF["track_id_update"] = keepGDF.groupby("track_id")["track_id_update"].cumsum()
    # keepGDF["track_id_combo"] = (
    #     keepGDF["track_id"].astype(int).astype(str)
    #     + "_"
    #     + keepGDF["track_id_update"].astype(str)
    # )
    # keepGDF["track_id"] = keepGDF["track_id_combo"]
    import gc

    gc.collect()
    return keepGDF
