from tqdm import tqdm
import pandas as pd
import geopandas as gpd
import os
import numpy as np
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
import itertools
from itertools import combinations

METADATA = {
    "order": "video order in one location",
    "video_location": "video location name",
    "track_id": "reconstructed track id, unique within each video",
    "video_id": "video id, unique within each location",
    "lat": "prejected latitude",
    "lon": "prejected longitude",
    "track_id_backup": "original track id from the tracking file",
    "speed_{n}s": "speed in meter per second",
    "speed_x_{n}s": "speed in meter per second in x direction",
    "speed_y_{n}s": "speed in meter per second in y direction",
    "hex_id": "h3 level 15 index",
    "frame_id": "reconstructed frame_id, across videos in a location, unique within one location",
    "frame_id_original": "original frame_id from the tracking file",
    "second_from_start": "calculated second from start based on the frame_id, 48 frames per real second",
    "appear_sec": "total second the track appeared in the video",
    "individual_frame_total": "total number of frames the track appeared in the video",
    "Social": "spatial cluster id, unique within each frame, disregarding invalid or valid across time",
    "frame_social_track": "frame_id + Social + track_id",
    "group_id_social": "frame_id + Social, unique within each video",
    "group_size": "number of tracks in the group",
    "is_group": "whether the track is in a group or not",
    "group_first_frame": "first frame_id when the track is in a group",
    "track_first_frame": "first frame_id when the track appear in this video",
    "group_track_delta": "difference between group_first_frame and track_first_frame",
    "emerging_group": "whether the group is newly formed or not",
    "cross_frame_group_id": "this is a group id that can be used to identify the group across frames (only available for current videos)",
    "timestamp": "timestamp of each frame (Only available for modern videos). use for reference.",
}

N = 2
VALID_THREAD = 0  # set this back to 2 later


def get_selcols(n=N):
    # format METADATA
    metadata = {x.format(n=n): y for x, y in METADATA.items()}
    return list(metadata.keys())


def generatecluster(df, dis, epsg):
    """
    This function go through each frame and run DBscan based on different Distance
    threshod

    """
    predlist = []
    for f in tqdm(df["frame_id"].unique()):
        preDF = df[df["frame_id"] == f].reset_index(drop=True)
        X = preDF[[f"x_{epsg}", f"y_{epsg}"]].values

        # eps : maximum distance between two samples
        # Here we use pixel distance for ease of visualization
        # 12 pixel for 0.5m, given hunman to human interaction distance maximum as 1.2 meter
        # https://en.wikipedia.org/wiki/Proxemics#:~:text=Hall%20described%20the%20interpersonal%20distances,and%20(4)%20public%20space.

        clustering = DBSCAN(eps=dis, min_samples=2).fit(X)
        pred = clustering.labels_
        predlist.append(pred)

    allpred = np.concatenate(predlist, axis=0)
    return allpred


def generate_social(traceGDF, epsg, dis=1.9):
    """
    d is the distance threshold for DBscan at meter
    """
    traceGDF = traceGDF.sort_values(["frame_id", "track_id"]).reset_index(drop=True)
    clusterlabel = generatecluster(traceGDF, dis, epsg)
    FPre = pd.DataFrame(clusterlabel, columns=["Social"])
    DBcluster = pd.concat([traceGDF, FPre], axis=1)

    DBcluster["frame_id"] = DBcluster["frame_id"].astype(int)
    # Drop those clusterlabel == -1, create a spatial cluster id
    DBcluster["group_id_social"] = (
        DBcluster["frame_id"].astype(str) + "_" + DBcluster["Social"].astype(str)
    )
    DBcluster["group_id_social"] = np.where(
        DBcluster["Social"] == -1, np.nan, DBcluster["group_id_social"]
    )
    DBSocial = DBcluster[DBcluster["Social"] != -1].reset_index(drop=True)
    # os.makedirs(outfolder+"/step1_dbscan")
    DBSocial["group_id_social"] = DBSocial["group_id_social"].astype(str)
    return DBSocial, DBcluster


def valid_link(DBSocial, x, y, thred=0.1, n=1):
    samplegroup = DBSocial[DBSocial["track_id"].isin([x, y])]
    # calculate the speed_x, speed_y correlation between track 10 and 11
    df_wide = samplegroup.pivot(
        index="frame_id",
        columns="track_id",
        values=[f"speed_x_{n}s", f"speed_y_{n}s", f"speed_{n}s"],
    ).reset_index()
    # calculate the correlation
    df_wide = df_wide.dropna()
    coor1 = df_wide[(f"speed_x_{n}s", x)].corr(df_wide[(f"speed_x_{n}s", y)])
    coor2 = df_wide[(f"speed_y_{n}s", x)].corr(df_wide[(f"speed_y_{n}s", y)])
    coor3 = df_wide[(f"speed_{n}s", x)].corr(df_wide[(f"speed_{n}s", y)])
    if coor1 > thred and coor2 > thred:
        return True
    else:
        return False


def getuvperframe(testdf, iditem):
    #     testdf = effDF[effDF['frame_id'] == frameid]
    U = []
    V = []
    groupid = []
    for i, group in tqdm(testdf.groupby([iditem])["track_id"]):

        # generate all combinations without replacement
        # from the group of similar column pairs
        for u, v in itertools.combinations(group, 2):
            U.append(u)
            V.append(v)
            groupid.append(i)

    dfframe = pd.DataFrame({"u": U, "v": V, iditem: groupid})

    return dfframe


def get_links(traceGDF, epsg=3857, timethred=4):

    # traceGDF = get_speed_vector(traceGDF)
    # create spatial cluster
    DBSocial, DBcluster = generate_social(traceGDF, epsg)

    # two person appear together for at least 5 second (60*2 frame per second )
    # or half of the appearing time

    selp = "social"
    # selp = 'personal_far'
    iditem = "group_id_{}".format(selp)
    df_links = getuvperframe(DBSocial, iditem)

    # First Aggregation, disregard time continuity, only consider frequency
    df_links = (
        df_links.groupby(["u", "v"]).size().reset_index().rename(columns={0: "weight"})
    )

    fps = 29.9
    # qualified link --> staying together more than 2.5 seconds and speed correlation higher than 10%
    # and the speed vector (x,y) have correlation more than 10%

    df_links["valid"] = df_links.apply(
        lambda x: valid_link(DBSocial, x["u"], x["v"]), axis=1
    )
    df_links_valid = df_links[
        (df_links["valid"] == True) & (df_links["weight"] > timethred * fps)
    ].reset_index(drop=True)

    return DBSocial, DBcluster, df_links_valid


def valid_link_corr(DBSocial, x, y, thred=0.5, n=1):
    samplegroup = DBSocial[DBSocial["track_id"].isin([x, y])]
    # calculate the speed_x, speed_y correlation between track 10 and 11
    df_wide = samplegroup.pivot(
        index="frame_id",
        columns="track_id",
        values=[f"speed_x_{n}s", f"speed_y_{n}s", f"speed_{n}s"],
    ).reset_index()
    # calculate the correlation
    df_wide = df_wide.dropna()

    coor1 = df_wide[(f"speed_x_{n}s", x)].corr(df_wide[(f"speed_x_{n}s", y)])
    coor2 = df_wide[(f"speed_y_{n}s", x)].corr(df_wide[(f"speed_y_{n}s", y)])
    coor3 = df_wide[(f"speed_{n}s", x)].corr(df_wide[(f"speed_{n}s", y)])
    # corr4 is a stay indicator, if both speed_{n}s <0.5, thenn it is a stay
    speed_mean1 = df_wide[(f"speed_{n}s", x)].mean()
    speed_mean2 = df_wide[(f"speed_{n}s", y)].mean()
    if speed_mean1 < 0.5 and speed_mean2 < 0.5:
        coor4 = 1
    else:
        coor4 = 0
    return coor1, coor2, coor3, coor4


def get_selfile(DBcluster, framsel, thre=2):

    seldb = DBcluster[DBcluster["frame_id"] == framsel].reset_index(drop=True)
    seldb = gpd.GeoDataFrame(
        seldb,
        geometry=[Point(x, y) for x, y in zip(seldb["lon"], seldb["lat"])],
        crs=f"EPSG:4326",
    )
    ax = seldb[seldb["Social"] != -1].plot(
        column="Social", legend=True, cmap="tab20", figsize=(8, 8)
    )
    seldb[seldb["Social"] == -1].plot(color="grey", ax=ax)

    seldb_shift = DBcluster[DBcluster["frame_id"] == framsel + thre * 2].reset_index(
        drop=True
    )
    seldb_shift = gpd.GeoDataFrame(
        seldb_shift,
        geometry=[Point(x, y) for x, y in zip(seldb_shift["lon"], seldb_shift["lat"])],
        crs=f"EPSG:4326",
    )
    ax = seldb_shift[seldb_shift["Social"] != -1].plot(
        column="Social", legend=True, cmap="tab20", figsize=(8, 8)
    )
    seldb_shift[seldb_shift["Social"] == -1].plot(color="grey", ax=ax)
    return seldb, seldb_shift


def link_method(traceGDF, DBSocial, DBcluster, df_links_valid, fps, interpolation=True):
    data_link = (
        DBSocial.groupby(["frame_id", "Social"])["track_id"].unique().reset_index()
    )
    data_link["group_member"] = data_link.apply(
        lambda x: "&&".join([str(i) for i in x["track_id"]]), axis=1
    )

    # measure group length
    data_link["group_len"] = data_link["track_id"].apply(lambda x: len(x))
    # make a list of all possible combination of 2 people
    data_link["combination2"] = data_link["track_id"].apply(
        lambda x: list(combinations(x, 2))
    )
    data_link_explode = (
        data_link[["frame_id", "Social", "combination2"]]
        .explode("combination2")
        .reset_index(drop=True)
    )
    data_link_explode["u_v"] = data_link_explode["combination2"].apply(
        lambda x: "&&".join([str(i) for i in x])
    )
    data_link_explode["v_u"] = data_link_explode["combination2"].apply(
        lambda x: "&&".join([str(i) for i in x[::-1]])
    )

    df_links_valid["u_v"] = df_links_valid.apply(
        lambda x: "&&".join([str(x["u"]), str(x["v"])]), axis=1
    )
    df_links_valid["v_u"] = df_links_valid.apply(
        lambda x: "&&".join([str(x["v"]), str(x["u"])]), axis=1
    )
    # check if the u_v combination exist in the valid link dataframe
    demolinks = data_link_explode[
        (data_link_explode["u_v"].isin(df_links_valid["u_v"].unique()))
        | (data_link_explode["u_v"].isin(df_links_valid["v_u"].unique()))
    ].reset_index(drop=True)
    # flatten the groups to each track
    demolinks = (
        demolinks[["frame_id", "Social", "combination2"]]
        .explode("combination2")
        .reset_index(drop=True)
        .sort_values(["frame_id", "Social"], ascending=False)
        .rename(columns={"combination2": "track_id"})
        .drop_duplicates(["frame_id", "Social", "track_id"])
        .reset_index(drop=True)
    )
    demolinks["frame_social_track"] = (
        demolinks["frame_id"].astype(str)
        + "$$"
        + demolinks["Social"].astype(str)
        + "$$"
        + demolinks["track_id"].astype(str)
    )

    # confirm the data can be merged back to the original data
    DBSocial["frame_social_track"] = (
        DBSocial["frame_id"].astype(str)
        + "$$"
        + DBSocial["Social"].astype(str)
        + "$$"
        + DBSocial["track_id"].astype(str)
    )
    DBSocial_update = DBSocial[
        DBSocial["frame_social_track"].isin(demolinks["frame_social_track"].unique())
    ].reset_index(drop=True)
    per = (
        DBSocial_update.shape[0] / DBcluster.shape[0]
    )  # 26% observation ever in a group
    # Social cluster id become the group id within each frame
    DBSocial_update["group_id_social"] = (
        DBSocial_update["frame_id"].astype(str)
        + "_"
        + DBSocial_update["Social"].astype(str)
    )

    # create the True Group ID
    DBSocial_group = (
        DBSocial_update.groupby(["frame_id", "Social"])["track_id"]
        .unique()
        .reset_index()
    )
    DBSocial_group["truegroup"] = DBSocial_group["track_id"].apply(
        lambda x: "&&".join(sorted([str(i) for i in x]))
    )  # add the sorted here so that we can ignore the order

    DBSocial_update = DBSocial_update[
        ["group_id_social", "frame_id", "Social", "track_id"]
    ].merge(
        DBSocial_group[["frame_id", "Social", "truegroup"]],
        on=["frame_id", "Social"],
        how="inner",
    )

    # for each track, if the frame_id within its group first and last frame, then it is a group
    def get_largergroup(DBSocial_group, DBcluster):
        DBsocial_group_update = []
        for truegroup in DBSocial_group["truegroup"].unique():
            temp = DBSocial_update[
                DBSocial_update["truegroup"] == truegroup
            ].reset_index(drop=True)
            trackls = temp["track_id"].unique()
            firstframe = temp["frame_id"].min()
            lastframe = temp["frame_id"].max()
            # print(temp.shape[0])}
            allvalid = DBcluster[
                (DBcluster["track_id"].isin(trackls))
                & (DBcluster["frame_id"] <= lastframe)
                & (DBcluster["frame_id"] >= firstframe)
            ]
            allvalid["truegroup"] = truegroup
            # print(allvalid.shape[0])
            DBsocial_group_update.append(allvalid)
        DBsocial_group_update = pd.concat(DBsocial_group_update).reset_index(drop=True)
        return DBsocial_group_update

    if interpolation == True:
        DBsocial_group_update = get_largergroup(DBSocial_group, DBcluster)
    else:
        DBsocial_group_update = DBSocial_group.copy()
    # NOW WE MAY HAVE DUPLICATES>> MERGE THEM >> EACH TRACK SHOULD ONLY HAVE ONE TRUEGROUP IN ONE FRAME

    # DBsocial_group_update = DBSocial_update.copy()

    DBsocial_group_update["group_id_social"] = (
        DBsocial_group_update["frame_id"].astype(str)
        + "_"
        + DBsocial_group_update["Social"].astype(str)
    )
    DBsocial_group_update["frame_social_track"] = (
        DBsocial_group_update["frame_id"].astype(str)
        + "$$"
        + DBsocial_group_update["Social"].astype(str)
        + "$$"
        + DBsocial_group_update["track_id"].astype(str)
    )
    DBsocial_group_update = DBsocial_group_update.drop_duplicates(
        ["frame_id", "track_id"]
    )

    DBcluster.drop("group_id_social", axis=1, inplace=True)

    DBcluster["frame_social_track"] = (
        DBcluster["frame_id"].astype(str)
        + "$$"
        + DBcluster["Social"].astype(str)
        + "$$"
        + DBcluster["track_id"].astype(str)
    )
    # DBcluster.drop('group_id_social', axis = 1, inplace = True)
    DBcluster_update = DBcluster.merge(
        DBsocial_group_update[["frame_social_track", "truegroup", "group_id_social"]],
        on="frame_social_track",
        how="left",
    )
    # merge the DBSocial_update back to the DBcluster
    DBcluster_update["is_group"] = np.where(
        DBcluster_update["group_id_social"].isnull(), False, True
    )

    # check if a group is newly formed or not
    # for each track, find its first frame_id when it is in a group
    DBcluster_update["group_first_frame"] = DBcluster_update.groupby(
        ["track_id", "is_group"]
    )["frame_id"].transform("min")
    DBcluster_update["group_last_frame"] = DBcluster_update.groupby(
        ["track_id", "is_group"]
    )["frame_id"].transform("max")
    DBcluster_update["group_first_frame"] = np.where(
        DBcluster_update["is_group"] == False,
        np.nan,
        DBcluster_update["group_first_frame"],
    )
    DBcluster_update["group_last_frame"] = np.where(
        DBcluster_update["is_group"] == False,
        np.nan,
        DBcluster_update["group_last_frame"],
    )

    DBcluster_update["track_first_frame"] = DBcluster_update.groupby(["track_id"])[
        "frame_id"
    ].transform("min")
    DBcluster_update["group_track_delta"] = (
        DBcluster_update["group_first_frame"] - DBcluster_update["track_first_frame"]
    )
    DBcluster_update["emerging_group"] = np.where(
        DBcluster_update["group_track_delta"] > 29.97 * 5, True, False
    )  # 5 second
    DBcluster_update = DBcluster_update.drop_duplicates(["track_id", "frame_id"])

    DBcluster_update["appear_sec"] = (
        DBcluster_update.groupby("track_id")["frame_id"].transform("count") / fps
    )
    DBcluster_update["individual_frame_total"] = DBcluster_update.groupby("track_id")[
        "frame_id"
    ].transform("count")
    DBcluster_update["group_size"] = (
        DBcluster_update["truegroup"].fillna("").apply(lambda x: len(x.split("&&")))
    )
    DBcluster_update.rename(
        columns={
            "truegroup": "cross_frame_group_id",
        },
        inplace=True,
    )
    selcols = get_selcols()
    exportcols = [x for x in selcols if x in DBcluster_update.columns]
    assert DBcluster_update.shape[0] == traceGDF.shape[0]
    return DBcluster_update[exportcols]


def generate_group_final(traceGDF, fps=29.97, n=0.5):
    traceGDF["appear_sec"] = (
        traceGDF.groupby("track_id")["frame_id"].transform("count") / fps
    )
    n_ori = traceGDF.shape[0]
    print("current size", n_ori)

    traceGDF = traceGDF[traceGDF["appear_sec"] > VALID_THREAD].reset_index(drop=True)
    n_after = traceGDF.shape[0]
    print("after drop", n_after)
    print(
        f"keeping tracks that appear more than {VALID_THREAD} seconds:", n_after / n_ori
    )
    if n_after == 0:
        print("no data remain")
    DBSocial, DBcluster = generate_social(traceGDF, 3857, dis=2.1)
    iditem = "group_id_social"
    df_links = getuvperframe(DBSocial, iditem)
    df_links = (
        df_links.groupby(["u", "v"]).size().reset_index().rename(columns={0: "weight"})
    )
    df_links = df_links[df_links["weight"] > 0.25 * fps].reset_index(drop=True)
    df_links["coor_ls"] = df_links.apply(
        lambda x: valid_link_corr(DBSocial, x["u"], x["v"], n=n), axis=1
    )
    df_links["valid"] = np.where(
        df_links["coor_ls"].apply(lambda x: x[0] > 0.0 or x[1] > 0.0), True, False
    )
    # links are valid if all people in a group are staying
    df_links["valid"] = np.where(
        df_links["coor_ls"].apply(lambda x: x[3] > 0), True, df_links["valid"]
    )

    df_links_valid = df_links[(df_links["valid"] == True)].reset_index(drop=True)
    DBcluster_update = link_method(
        traceGDF, DBSocial, DBcluster, df_links_valid, fps, interpolation=True
    )
    return DBcluster_update
