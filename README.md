# Overview
* This is the scripts that processed the pedestrian detection output (after georeference) and generates:
1. the group behavior indicators
2. temporal speed
* To know how to calibrate the pedestrian detection output to real-world coordinates, please refer to Step 1 [link](https://medium.com/@yuanzfan16/pedestrian-in-groups-analysis-i-single-fixed-camera-video-to-bev-transformation-using-1f9177e125ef).

## Usage
python>=3.8
### Input
common object detection output with these fields
```
frame_id, track_id, x,y,w,h, latitude, longitude
```
run `main.py` to transform the sample csv and get group detection results

**Sample data is available from researchers upon requests**

## Citation
```
@techreport{salazar2024shifting,
  title={Shifting Patterns of Social Interaction: Exploring the Social Life of Urban Spaces Through AI},
  author={Salazar-Miranda, Arianna and Fan, Zhuangyuan and Baick, Michael B and Hampton, Keith N and Duarte, Fabio and Loo, Becky PY and Glaeser, Edward L and Ratti, Carlo},
  year={2024},
  institution={National Bureau of Economic Research}
}
@article{loo2023social,
  title={Social interaction in public space: Spatial edges, moveable furniture, and visual landmarks},
  author={Loo, Becky PY and Fan, Zhuangyuan},
  journal={Environment and Planning B: Urban Analytics and City Science},
  volume={50},
  number={9},
  pages={2510--2526},
  year={2023},
  publisher={SAGE Publications Sage UK: London, England}
}
```