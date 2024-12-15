# load projected data
import pandas as pd
import geopandas as gpd
import os
import numpy as np
from shapely.geometry import Point


def load_video(videoname, video_start_at, video_group, destfolder, video_start_frame=0):
    traceGDF = pd.read_csv(os.path.join(destfolder, f"{videoname}_projected.csv"))
    traceGDF = traceGDF[traceGDF["frame_id"] > video_start_frame].reset_index(drop=True)
    traceGDF["timestamp"] = video_start_at + traceGDF["frame_id"].apply(
        lambda x: pd.Timedelta(seconds=x / 29.97)
    )
    traceGDF["video_group"] = video_group
    traceGDF["videoname"] = videoname
    return traceGDF


def get_speed_vector(keepGDF, n=0.5, fps=29.97, globalcrs="EPSG:3857"):
    """This function calculate the speed vector for each track"""
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

    testgdf["track_id_backup"] = testgdf["track_id"]
    testgdf["track_id_break"] = np.where(testgdf["dist"] > 1, 1, 0)
    testgdf["track_id_update"] = testgdf["track_id_break"].fillna(0).astype(int)
    testgdf["track_id_update"] = testgdf.groupby("track_id")["track_id_update"].cumsum()
    testgdf["track_id_combo"] = (
        testgdf["track_id"].astype(int).astype(str)
        + "_"
        + testgdf["track_id_update"].astype(str)
    )
    testgdf["track_id"] = testgdf["track_id_combo"]

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
    import gc

    gc.collect()
    return keepGDF
