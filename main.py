import numpy as np
from matplotlib import pyplot as plt
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import h3
from util.speed import *
from util.group import *

# Set up constants
FPS = 29.97002997002997
DATA_FOLDER = "_data"
# these are known feature of the video
videoname = "20081008-141944b08"
video_group = videoname[:-3]
video_start_at = pd.to_datetime("2008-10-08T15:24:16")
video_start_frame = 0
loc_name = "bryant_park"


def load_video(videoname, video_start_at, video_group, destfolder, video_start_frame=0):
    # Load the video data
    traceGDF = pd.read_csv(
        os.path.join(destfolder, f"{videoname}_projected.csv"),
        parse_dates=["timestamp"],
    )
    traceGDF["frame"] = traceGDF["frame"] + video_start_frame
    traceGDF["video_group"] = video_group
    traceGDF["video_start_at"] = video_start_at
    traceGDF["video_start_frame"] = video_start_frame
    return traceGDF


def main():
    traceGDF = load_video(
        videoname,
        video_start_at,
        video_group,
        destfolder=DATA_FOLDER,
        video_start_frame=video_start_frame,
    )
    traceGDF = get_speed_vector(traceGDF, n=0.5)
    traceGDF["video_location"] = loc_name
    traceGDF["second_from_start"] = traceGDF["timestamp"].apply(
        lambda x: x.hour * 3600 + x.minute * 60 + x.second
    )
    traceGDF["hex_id"] = traceGDF.apply(
        lambda x: h3.geo_to_h3(x["lat"], x["lon"], 15), axis=1
    )
    traceGDF.to_csv(os.path.join(DATA_FOLDER, "stage1_trace.csv"), index=False)

    groupGDF = generate_group_final(traceGDF)
    groupGDF.to_csv(os.path.join(DATA_FOLDER, "stage2_group.csv"), index=False)
    print("Done")

    return traceGDF, groupGDF


if __name__ == "__main__":
    traceGDF, groupGDF = main()
