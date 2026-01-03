from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from src.config import SimulationConfig
from src.data_matrices import Building, Floor
from src import enums as bo_enums


def _encode_value(v: Any) -> Any:
    if isinstance(v, Enum):
        return {"__enum__": f"{v.__class__.__name__}.{v.name}"}
    if is_dataclass(v):
        return {k: _encode_value(val) for k, val in asdict(v).items()}
    if isinstance(v, (list, tuple)):
        return [_encode_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _encode_value(val) for k, val in v.items()}
    return v


def _decode_enum(maybe_enum: Any) -> Any:
    if isinstance(maybe_enum, dict) and "__enum__" in maybe_enum:
        enum_str = maybe_enum["__enum__"]  # e.g. "TabuStrategy.BLOCK_ROUTER_ID"
        enum_cls_name, enum_member = enum_str.split(".", 1)
        enum_cls = getattr(bo_enums, enum_cls_name)
        return enum_cls[enum_member]
    return maybe_enum


def _decode_value(v: Any) -> Any:
    if isinstance(v, dict):
        if "__enum__" in v:
            return _decode_enum(v)
        return {k: _decode_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_decode_value(x) for x in v]
    return v


def snapshot_to_npz(path: str | Path, *, config: SimulationConfig, building: Building) -> None:
    """
    Zapisuje CAŁĄ symulację do jednego pliku .npz:
    - parametry config (json)
    - wszystkie piętra: wall/router/cover + thickness
    """
    path = Path(path)

    config_dict = asdict(config)
    config_json = json.dumps(_encode_value(config_dict), ensure_ascii=False)

    floors = building.Floor_list
    payload: dict[str, Any] = {
        "config_json": np.array(config_json),
        "floor_count": np.array(len(floors), dtype=np.int32),
        "floor_heights": np.array(float(config.floor_heights), dtype=np.float64),
    }

    for i, fl in enumerate(floors):
        payload[f"wall_{i}"] = np.asarray(fl.wall_matrix, dtype=np.float64)
        payload[f"router_{i}"] = np.asarray(fl.router, dtype=bool)
        payload[f"cover_{i}"] = np.asarray(fl.cover, dtype=np.int32)
        payload[f"thickness_{i}"] = np.array(float(fl.Floor_thickness), dtype=np.float64)

    np.savez_compressed(path, **payload)


def snapshot_from_npz(path: str | Path) -> tuple[SimulationConfig, Building]:
    """
    Wczytuje symulację z pliku .npz i zwraca (config, building).
    """
    path = Path(path)

    with np.load(path, allow_pickle=False) as data:
        config_json = str(data["config_json"].item())
        config_raw = json.loads(config_json)
        config_dict = _decode_value(config_raw)

        config = SimulationConfig()
        for k, v in config_dict.items():
            if hasattr(config, k):
                setattr(config, k, v)

        floor_count = int(data["floor_count"].item())

        floors: list[Floor] = []
        for i in range(floor_count):
            wall = np.array(data[f"wall_{i}"], dtype=np.float64)
            router = np.array(data[f"router_{i}"], dtype=bool)
            cover = np.array(data[f"cover_{i}"], dtype=np.int32)
            thickness = float(data[f"thickness_{i}"].item())

            floors.append(
                Floor(
                    wall_matrix=wall,
                    router_matrix=router,
                    cover_matrix=cover,
                    Floor_number=i,
                    Floor_thickness=thickness,
                )
            )

    building = Building(Floors=floors, Floor_heights=float(config.floor_heights), available_routers=[], config=config)
    return config, building