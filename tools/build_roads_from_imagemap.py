"""
Generate road, intersection and exit features into data/map.geojson
from the image-map coordinate strings used in index.html.

Usage (from project root):

    python tools/build_roads_from_imagemap.py

The script will:
  - Read existing zones & rivers from data/map.geojson
  - Remove any previous features with type in {"road", "intersection"}
  - Add LineString features for each road polyline
  - Detect intersections (points shared by >= 2 roads)
  - Mark intersections that touch the map border as exits
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict


ROOT = Path(__file__).resolve().parents[1]
GEOJSON_PATH = ROOT / "data" / "map.geojson"

# These are the approximate pixel dimensions of the planning image.
# They are only used to detect "exit" nodes near the border.
IMAGE_WIDTH = 1984
IMAGE_HEIGHT = 1907
EDGE_MARGIN = 30  # pixels


@dataclass
class RoadDef:
  id: str
  name: str
  level: str  # e.g. "primary", "secondary", "local"
  coords_str: str

  def parsed_coords(self) -> List[Tuple[float, float]]:
    nums = [float(v) for v in self.coords_str.split(",") if v.strip()]
    if len(nums) % 2 != 0:
      raise ValueError(f"Odd number of coordinates for road {self.id}")
    coords: List[Tuple[float, float]] = []
    for i in range(0, len(nums), 2):
      x, y = nums[i], nums[i + 1]
      coords.append((x, y))
    return coords


# Roads copied from the image-map coordinate strings used in index.html
ROAD_DEFS: List[RoadDef] = [
  # Original road network
  RoadDef(
    id="R01_main_vertical_right",
    name="Main vertical road (right)",
    level="primary",
    coords_str=(
      "937,1942,937,1902,934,1850,932,1790,930,1720,930,1668,936,1607,937,1556,"
      "934,1485,936,1437,939,1391,936,1338,932,1287,937,1241,936,1201,939,1141,"
      "941,1089,941,1042,943,996,944,957,943,911,939,858,941,809,937,765,937,721,"
      "939,685,937,638,937,606,934,560,937,514,934,452,930,396,930,341,930,290,"
      "934,249,936,193,937,147,930,101,930,53,930,16"
    ),
  ),
  RoadDef(
    id="R02_main_vertical_left",
    name="Main vertical road (left)",
    level="primary",
    coords_str=(
      "228,1404,228,1365,226,1323,228,1280,224,1238,222,1194,229,1155,231,1107,"
      "226,1052,229,996,231,955,231,906,231,856,229,804,229,758,233,719,229,673,"
      "228,631,228,579,233,539,238,500,238,463,235,428,235,389,237,343,237,308,"
      "237,267,238,225,237,184,238,150,238,115,238,87,238,48,237,16"
    ),
  ),
  RoadDef(
    id="R03_mid_horizontal_between_verticals",
    name="Mid horizontal road between verticals",
    level="secondary",
    coords_str=(
      "946,1397,897,1395,851,1395,796,1398,754,1393,711,1397,676,1395,634,1397,"
      "588,1393,544,1398,498,1393,455,1393,420,1393,374,1393,330,1386,291,1393,"
      "249,1386,226,1386"
    ),
  ),
  RoadDef(
    id="R04_lower_riverfront_curved",
    name="Lower riverfront curved road",
    level="primary",
    coords_str=(
      "28,1195,69,1199,104,1195,147,1195,192,1197,231,1195,288,1195,351,1201,"
      "415,1206,471,1206,514,1204,565,1202,605,1202,651,1206,687,1206,731,1206,"
      "778,1206,824,1206,865,1206,907,1204,944,1208,981,1202,1036,1201,1080,1195,"
      "1126,1183,1169,1174,1199,1162,1237,1146,1283,1120,1319,1089,1354,1059,"
      "1384,1033,1419,1005,1451,969,1479,936,1509,913,1536,876,1568,844,1594,814,"
      "1617,788,1645,759,1665,736,1696,715,1735,696,1778,673,1806,655,1843,643,"
      "1875,616,1901,602,1933,581"
    ),
  ),
  RoadDef(
    id="R05_middle_vertical_small",
    name="Middle small vertical road",
    level="secondary",
    coords_str=(
      "362,1201,371,1157,372,1114,376,1065,372,1021,371,962,372,920,372,858,374,"
      "805,376,765,372,726,376,682,372,648,369,616"
    ),
  ),
  RoadDef(
    id="R06_upper_arc_main",
    name="Upper arc main road",
    level="primary",
    coords_str=(
      "55,609,104,609,143,609,189,609,231,615,259,609,312,618,364,620,413,623,"
      "448,622,496,623,542,623,591,623,650,627,704,627,741,623,782,625,821,631,"
      "867,631,909,631,946,631,994,631,1050,636,1098,638,1140,638,1199,638,1241,"
      "639,1283,639,1327,645,1368,639,1405,638,1440,632,1467,604,1492,572,1511,"
      "533,1530,503,1546,443,1550,383,1557,325,1557,269,1557,223,1559,177,1553,"
      "127,1562,94,1559,50,1559,20"
    ),
  ),
  RoadDef(
    id="R07_inner_arc_connecting_high_area",
    name="Inner arc connecting to high area",
    level="secondary",
    coords_str=(
      "365,1026,397,1026,431,1024,480,1028,528,1029,563,1026,609,1026,650,1028,"
      "701,1031,750,1031,793,1033,837,1033,895,1033,946,1042,987,1038,1033,1037,"
      "1073,1029,1102,1015,1124,1007,1156,991,1181,973,1204,943,1229,920,1248,"
      "894,1271,872,1287,849,1308,823,1336,781,1363,751,1384,708,1416,673,1435,"
      "650,1462,615,1493,574,1516,532,1536,496,1553,454,1559,413,1560,369,1559,"
      "318,1555,265,1555,216,1560,170,1562,127,1560,96,1560,60,1557,27"
    ),
  ),
  # RoadAdded group
  RoadDef(
    id="R08_vertical_additional_center",
    name="Additional vertical road near center",
    level="secondary",
    coords_str=(
      "454,622,454,555,454,482,451,415,454,345,454,283,460,231,460,166,460,111,"
      "457,67,454,29"
    ),
  ),
  RoadDef(
    id="R09_top_border",
    name="Top border road",
    level="primary",
    coords_str="19,33,1969,39",
  ),
  RoadDef(
    id="R10_upper_inner_left",
    name="Upper inner road (left segment)",
    level="secondary",
    coords_str="468,287,521,287,693,293,871,295,944,293",
  ),
  RoadDef(
    id="R11_middle_inner_left",
    name="Middle inner road (left segment)",
    level="secondary",
    coords_str="451,459,509,459,684,465,874,474,941,479",
  ),
  RoadDef(
    id="R12_upper_inner_right",
    name="Upper inner road (right segment)",
    level="secondary",
    coords_str="1035,293,1099,293,1262,295,1461,298,1557,284",
  ),
  RoadDef(
    id="R13_middle_inner_right",
    name="Middle inner road (right segment)",
    level="secondary",
    coords_str="1046,479,1146,479,1268,479,1385,482,1484,494,1543,468",
  ),
  RoadDef(
    id="R14_vertical_small_right",
    name="Small vertical road (right side)",
    level="secondary",
    coords_str="1262,482,1257,441,1260,389,1257,342,1257,293",
  ),
  RoadDef(
    id="R15_right_connector_to_riverfront",
    name="Right connector to riverfront",
    level="primary",
    coords_str=(
      "1934,888,1899,850,1858,812,1823,768,1791,731,1747,687,1712,655,1668,611,"
      "1622,567,1587,517,1554,468,1554,383,1557,293,1557,220,1554,149,1557,88,"
      "1554,53"
    ),
  ),
  RoadDef(
    id="R16_vertical_mid_right_added",
    name="Additional vertical road (mid-right)",
    level="secondary",
    coords_str=(
      "1038,637,1041,596,1041,552,1041,509,1041,456,1038,409,1038,354,1041,307,"
      "1041,269,1041,225,1041,179,1038,141,1041,100,1041,68,1041,30"
    ),
  ),
]


def is_near_edge(x: float, y: float) -> Tuple[bool, str | None]:
  """Return (is_exit, side_string) where side_string encodes edges touched."""
  sides = []
  if x <= EDGE_MARGIN:
    sides.append("west")
  elif x >= IMAGE_WIDTH - EDGE_MARGIN:
    sides.append("east")
  if y <= EDGE_MARGIN:
    sides.append("north")
  elif y >= IMAGE_HEIGHT - EDGE_MARGIN:
    sides.append("south")
  if not sides:
    return False, None
  return True, ",".join(sides)


def main() -> None:
  if not GEOJSON_PATH.exists():
    raise SystemExit(f"GeoJSON file not found: {GEOJSON_PATH}")

  with GEOJSON_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

  features = data.get("features", [])

  # Remove any previous road / intersection features so we regenerate cleanly
  kept_features = [
    f for f in features
    if f.get("properties", {}).get("type") not in {"road", "intersection"}
  ]

  road_features = []
  intersection_counter: Counter[Tuple[int, int]] = Counter()

  # Build road LineStrings and collect node counts
  for rd in ROAD_DEFS:
    coords = rd.parsed_coords()
    for x, y in coords:
      key = (round(x), round(y))
      intersection_counter[key] += 1

    road_features.append(
      {
        "type": "Feature",
        "properties": {
          "type": "road",
          "id": rd.id,
          "name": rd.name,
          "level": rd.level,
        },
        "geometry": {
          "type": "LineString",
          "coordinates": [[x, y] for (x, y) in coords],
        },
      }
    )

  # Build intersection (and exit) nodes
  intersection_features = []
  node_index = 1

  for (x_i, y_i), count in intersection_counter.items():
    is_exit, side = is_near_edge(x_i, y_i)

    # Create nodes if:
    #  - true intersection (>=2 roads)
    #  - OR this point is an exit (touches border)
    if count < 2 and not is_exit:
      continue

    props: Dict[str, object] = {
      "type": "intersection",
      "id": f"INT_{node_index}",
      "degree": int(count),
    }
    if is_exit:
      props["is_exit"] = True
      props["exit_side"] = side
    else:
      props["is_exit"] = False

    intersection_features.append(
      {
        "type": "Feature",
        "properties": props,
        "geometry": {
          "type": "Point",
          "coordinates": [float(x_i), float(y_i)],
        },
      }
    )
    node_index += 1

  data["features"] = kept_features + road_features + intersection_features

  GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
  with GEOJSON_PATH.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

  print(
    f"Wrote {len(road_features)} roads and "
    f"{len(intersection_features)} intersections to {GEOJSON_PATH}"
  )


if __name__ == "__main__":
  main()


