---
status: ["not started", "done", "in progress"]
---

# Urban Visual Intelligence Project 02 - Public Space from 1980 to 2008
This project shares code for colleboration on the video analysis project.

# Project Roadmap
## 1. Video Cleaning for both historical and modern videos
- [ ] Seperate videos into scenes, and pick the scenes lasted more than 15 video seconds
- [ ] Export example frames for each selected scene
- [ ] Generate geotiff via QGIS from each example frame. See method [here](https://docs.google.com/document/d/17b7tm3fHhAhNPlTBfhLpZodYa7NLsZ7xV14CJxv3Gwc/edit?usp=share_link)
- [ ] Locate location of all videos and scenes
- [ ] Classify location type of all videos and scenes
- [ ] Predict pedestrian location for each videos
- [ ] Transform the pedestrian location to the ground
- [ ] Draw effective observation boundary for each scene in QGIS
- [ ] Mark the scene's time recorded (1980-MM-DD HH:MM)

## 2. Algorithm and scripts development
- [ ] Run human attribute models on all videos to be predicted
- [ ] Refine the grouping detection algorithm
  - [ ] Clarify thresholds for grouping detection
- [ ] Behavior detection (exploration stage)

## 3. Additional data acquiring
- [ ] Adjacent POIs for each selected scenes (buffer from the point of video for 50 meter)
- [ ] Adjacent population density estimation (same buffer size)
- [ ] Land use changes

## 4. Analysis to answer the research questions
- [ ] Pedestrian distribution space
- [ ] Pedestrian moving speed
- [ ] Group size
- [ ] Group gender composition
- [ ] Group speed
- [ ] Group formation (emerging or exisiting)
- [ ] Group activity type

