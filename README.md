# Data Organization
* Transactional data: /home/yuanzf/WW/_data (10.89.0.59)
* Static data: NAS server /home/Arianna drive (10.89.0.29)

# Script Organization
## 1. Split historical to scenes (Manual work)
Historical videos are seperated into different scenes: refer to googl sheet: https://docs.google.com/spreadsheets/d/1djLf9Uhh1zJpPBiSyjTnZ_EkkP1uZf2L8Rg8XWmXKlY/edit#gid=1319519320
Valid scenes are saved under: `../_data/08_historical_valid_scene/Scenes`

## Flip the video vertically and augment the video to make up the skipped intervals
Each scene is first flipped then augment to 16 times (GPU required) Tool: https://github.com/megvii-research/ECCV2022-RIFE
Flipped videos saved under: `../_data/08_historical_valid_scene/Scenes_r` (some videos are flipped in server directly)

```
cd ECCV2022-RIFE
python3 inference_video.py --exp=4 --video=/lustre1/g/geog_pyloo/06_WW/_raw/video_historical_scenes_r/B11_G1_Env3_0001-Scene-001.mp4 --output=/lustre1/g/geog_pyloo/06_WW/_raw/video_historical_scenes_r_4x/B11_G1_Env3_0001-Scene-001.mp4
```

## 2. Generate frames from videos for labeling
```
./process_current_videos/00_generate_frame_labeling.ipynb
```

## 3. Label the image via ROBOFLOW
https://app.roboflow.com/hkupyloo/historical-video-pedestrian-detection/3

## 4. Training and Deployment
### Historical video uses YOLOv5 + Deepsort retrained model
1. Train YOLOv5 detection on 70 frames- (tutorial)[https://github.com/ultralytics/yolov5]
2. Current new version created and finetuned for this project (here)[https://github.com/brookefzy/uvi-yolov5-deepsort]
3. Combine the YOLOv5 new weights with Deepsort and make prediction. Results here: 
* txt: `../_data/03_tracking_result/_old_videos/yolo5_deepsort`
* viz: `../_data/03_tracking_result/_old_videos_viz`

### 5. Current video (except MET) uses PaddleDetection Attribution Detection + Deepsort+ YOLO
Paddle Detection Git repo: https://github.com/PaddlePaddle/PaddleDetection/blob/release/2.6/deploy/pipeline/docs/tutorials/pphuman_attribute.md

```
python deploy/pipeline/pipeline_no_video_output.py \
 --config deploy/pipeline/config/infer_cfg_pphuman.yml \
 -o ATTR.model_dir=output_inference/PPLCNet_x1_0_person_attribute_945_infer/ \
 --video_file="/lustre1/g/geog_pyloo/06_WW/_raw/videos_current/Met Steps videos (NEW)/20100612-082221/20100612-082221b09.avi" \
 --device=gpu
        
```

## 6. Georeferencing:
Refer to the tutorial on google doc: 
1. All frame sample for transformation in: `../_data/08_historical_valid_scene/Frames`
2. Transformed points: `../_data/08_historical_valid_scene/Frames`
3. Transformed points for current videos: 

## 7. Processing steps:
1. 02_detection_projection*: project the data to real world coordinates
2. 03_speed_comp.ipynb
* detecting jumping tracks and assign the track_id to a new person
* compute speed at given time interval.
3. 04_groud_aggregation: 
* aggregate the data to spatial units
* find if the data is inside or outside of the study area.
* assign realworld second
4. 05_group_historical (05_groupIdentify.ipynb):
* find each individual's associated group

## 8. Data Summary and Visualization
./12_data_summary_viz.ipynb

## Group Threshold Experiments
* 20230710: 4 second staying together minimum, link correlation >0
* 20230711: loose definition: 1 second staying together, link correlation >0
* 20230711b: loose defintiion: 1 second staying together, disregarding link correlation
* 20230711c: 1 second staying together, link correlation x AND y direction >0 or all people in a group stopped (speed<0.5)
**20230711d (final pick)**: 1 second staying together, link correlation x OR y direction >0 or all people in a group stopped (speed<0.5)


# Data Folder Structure
```
../_data
├── 00_raw                         # all raw video data
├── 02_siteplan                    # all plans for georeference (modern videos)
├── 03_tracking_result             # all video tracking results
├── 05_tracking_result_projected   # this folder contains files used for group behavior detection
├── 08_historical_valid_scene      # Historical videos were divided into scenes, sample frames, and geo-referenced frames
├── 10_clean                       # Cleaned data for visualization and analysis
└── 98_demo                        # Video example to show the detection, stay and group behaviors
```

# Data indexing
index of historical videos (here)[https://docs.google.com/spreadsheets/d/1djLf9Uhh1zJpPBiSyjTnZ_EkkP1uZf2L8Rg8XWmXKlY/edit?usp=sharing].

# Presentation
Most recent presentation file (here)[https://docs.google.com/presentation/d/1v8cMoHUJudcKl3XI_d4tk5g912uy_agu-fPuDWOD-cg/edit?usp=sharing]

# Methodology docs
Documentation on detail methodologies (here)[https://docs.google.com/document/d/17b7tm3fHhAhNPlTBfhLpZodYa7NLsZ7xV14CJxv3Gwc/edit?usp=drive_link]# mapboxjs
