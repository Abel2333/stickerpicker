# maunium-stickerpicker - A fast and simple Matrix sticker picker widget.
# Copyright (C) 2020 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from functools import partial
from io import BytesIO
import os.path
import json
from pathlib import Path
from typing import Dict, List

from PIL import Image

from . import matrix

open_utf8 = partial(open, encoding="UTF-8")


def is_animated_image(data: bytes) -> bool:
    with Image.open(BytesIO(data)) as image:
        return (
            getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1
        )


def get_display_size(
    data: bytes, max_w: int = 256, max_h: int = 256
) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        w, h = image.size

    if w > max_w or h > max_h:
        if w > h:
            h = int(h / (w / max_w))
            w = max_w
        else:
            w = int(w / (h / max_h))
            h = max_h

    return w, h


def convert_static_image(
    data: bytes, max_w: int = 256, max_h: int = 256
) -> tuple[bytes, int, int]:
    with Image.open(BytesIO(data)) as image:
        converted = image.convert("RGBA")
        new_file = BytesIO()
        converted.save(new_file, "PNG")

    w, h = get_display_size(data, max_w, max_h)
    return new_file.getvalue(), w, h


def prepare_image_for_upload(
    data: bytes, mime: str, max_w: int = 256, max_h: int = 256
) -> tuple[bytes, str, int, int]:
    w, h = get_display_size(data, max_w=max_w, max_h=max_h)

    if mime == "image/gif" and is_animated_image(data):
        return data, mime, w, h

    converted_data, w, h = convert_static_image(data, max_w=max_w, max_h=max_h)

    return converted_data, "image/png", w, h


def add_to_index(name: str, output_dir: str) -> None:
    index_path = os.path.join(output_dir, "index.json")
    try:
        with open_utf8(index_path) as index_file:
            index_data = json.load(index_file)
    except (FileNotFoundError, json.JSONDecodeError):
        index_data = {"packs": []}
    if "homeserver_url" not in index_data and matrix.homeserver_url:
        index_data["homeserver_url"] = matrix.homeserver_url
    if name not in index_data["packs"]:
        index_data["packs"].append(name)
        with open_utf8(index_path, "w") as index_file:
            json.dump(index_data, index_file, indent="  ")
        print(f"Added {name} to {index_path}")


def make_sticker(
    mxc: str, width: int, height: int, size: int, body: str = "", mimetype: str = "image/png"
) -> matrix.StickerInfo:
    return {
        "body": body,
        "url": mxc,
        "info": {
            "w": width,
            "h": height,
            "size": size,
            "mimetype": mimetype,
            # Element iOS compatibility hack
            "thumbnail_url": mxc,
            "thumbnail_info": {
                "w": width,
                "h": height,
                "size": size,
                "mimetype": mimetype,
            },
        },
        "msgtype": "m.sticker",
    }


def add_thumbnails(
    stickers: List[matrix.StickerInfo], stickers_data: Dict[str, bytes], output_dir: str
) -> None:
    thumbnails = Path(output_dir, "thumbnails")
    thumbnails.mkdir(parents=True, exist_ok=True)

    for sticker in stickers:
        image_data, _, _ = convert_static_image(stickers_data[sticker["url"]], 128, 128)

        name = sticker["url"].split("/")[-1]
        thumbnail_path = thumbnails / name
        thumbnail_path.write_bytes(image_data)
