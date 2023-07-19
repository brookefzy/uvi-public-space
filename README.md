---
status: ["not started", "done", "in progress"]
---

# Urban Visual Intelligence Project 02 - Public Space from 1980 to 2008
This project shares code for colleboration on the video analysis project.

# Project Roadmap
## 1. Video Cleaning for both historical and modern videos
- [x] Seperate videos into scenes, and pick the scenes lasted more than 15 video seconds. `done`
- [x] Export example frames for each selected scene `done`
- [x] Generate geotiff via QGIS from each example frame. See method [here](https://docs.google.com/document/d/17b7tm3fHhAhNPlTBfhLpZodYa7NLsZ7xV14CJxv3Gwc/edit?usp=share_link) `done`
- [x] Locate location of all videos and scenes `done`
- [x] Classify location type of all videos and scenes `done`
- [x] Predict pedestrian location for each videos `done`
- [x] Transform the pedestrian location to the ground `done`
- [x] Draw effective observation boundary for each scene in QGIS `not started`
- [x] Mark the scene's time recorded (1980-MM-DD HH:MM) `not started`

## 2. Algorithm and scripts development
- [x] Run human attribute models on all modern videos `done`
- [x] Refine the grouping detection algorithm `done`
  - [x] Clarify thresholds for grouping detection `in progress`
- [x] Behavior detection (exploration stage) `not started`

## 3. Additional data acquiring
- [ ] Adjacent POIs for each selected scenes (buffer from the point of video for 50 meter) `not started`
- [ ] Adjacent population density estimation (same buffer size) `not started`
- [ ] Land use changes `not started`

## 4. Analysis to answer the research questions
- [x] Pedestrian distribution space `done`
- [x] Pedestrian moving speed `done`
- [x] Group size `done`
- [x] Group gender composition `dropped`
- [x] Group speed `done`
- [x] Group formation (emerging or exisiting) `done`
- [x] Group activity type `not started`

