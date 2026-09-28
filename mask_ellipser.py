import json
import math

import numpy as np
import torch
import torch.nn.functional as F

try:
    from scipy import ndimage as _ndi
except Exception:  # scipy is optional
    _ndi = None


SHAPES = {
    "Ellipse (inscribed in bounding box)": "ellipse",
    "Circle (shorter side)": "circle_min",
    "Circle (longer side)": "circle_max",
}
REGION_MODES = ["Each region separately", "Merge all into one"]
CONNECTIVITY = ["8-connected", "4-connected"]


def _label_regions(binary_np, eight):
    """Label connected regions. Returns (labels[H, W] int array, count)."""
    if _ndi is not None:
        structure = np.ones((3, 3), dtype=int) if eight else None
        labels, n = _ndi.label(binary_np, structure=structure)
        return labels, int(n)

    # Fallback without scipy: propagate the max id through each region.
    binary = torch.from_numpy(binary_np.astype(np.float32))[None, None]
    H, W = binary_np.shape
    ids = torch.arange(1, H * W + 1, dtype=torch.float32).view(1, 1, H, W) * binary
    for _ in range(H + W):
        if eight:
            nxt = F.max_pool2d(ids, 3, 1, 1)
        else:
            nxt = torch.maximum(
                F.max_pool2d(ids, (1, 3), 1, (0, 1)),
                F.max_pool2d(ids, (3, 1), 1, (1, 0)),
            )
        nxt = nxt * binary
        if torch.equal(nxt, ids):
            break
        ids = nxt
    ids = ids[0, 0].numpy().astype(np.int64)
    uniq = np.unique(ids[ids > 0])
    remap = np.zeros(int(ids.max()) + 1, dtype=np.int64)
    remap[uniq] = np.arange(1, len(uniq) + 1)
    return remap[ids], len(uniq)


def _region_boxes(labels, n):
    """Return a list of (x0, y0, x1, y1, area) for labels 1..n (x1/y1 exclusive)."""
    areas = np.bincount(labels.ravel(), minlength=n + 1)
    boxes = []
    if _ndi is not None:
        for k, sl in enumerate(_ndi.find_objects(labels), start=1):
            if sl is None:
                continue
            ys, xs = sl
            boxes.append((xs.start, ys.start, xs.stop, ys.stop, int(areas[k])))
    else:
        for k in range(1, n + 1):
            ys, xs = np.where(labels == k)
            if len(ys):
                boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, int(areas[k])))
    return boxes


def _ellipse_patch(H, W, cx, cy, rx, ry, feather, device):
    """Render an ellipse only inside its local window. Returns (y0, y1, x0, x1, alpha)."""
    x0 = max(int(math.floor(cx - rx)) - 1, 0)
    x1 = min(int(math.ceil(cx + rx)) + 1, W)
    y0 = max(int(math.floor(cy - ry)) - 1, 0)
    y1 = min(int(math.ceil(cy + ry)) + 1, H)
    if x0 >= x1 or y0 >= y1:
        return None
    yy = torch.arange(y0, y1, device=device, dtype=torch.float32).view(-1, 1) + 0.5
    xx = torch.arange(x0, x1, device=device, dtype=torch.float32).view(1, -1) + 0.5
    d = torch.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    if feather > 0:
        alpha = ((1.0 - d) * min(rx, ry) / float(feather)).clamp(0.0, 1.0)
    else:
        alpha = (d <= 1.0).float()
    return y0, y1, x0, x1, alpha


class MaskEllipser:
    """Turn rectangular (or any-shaped) masks into ellipses / circles.

    Every connected region is converted on its own, based on its own bounding box.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "shape": (list(SHAPES.keys()),),
                "region_mode": (REGION_MODES,),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.01}),
                "feather": ("INT", {"default": 0, "min": 0, "max": 1024, "step": 1}),
                "min_area": ("INT", {"default": 1, "min": 1, "max": 100000000, "step": 1}),
                "connectivity": (CONNECTIVITY,),
            }
        }

    RETURN_TYPES = ("MASK", "MASK", "STRING", "INT")
    RETURN_NAMES = ("mask", "individual_masks", "bboxes", "count")
    FUNCTION = "convert"
    CATEGORY = "mask"

    def convert(self, mask, shape, region_mode, threshold, scale, feather, min_area, connectivity):
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)
        B, H, W = mask.shape
        device = mask.device
        mode = SHAPES[shape]
        eight = connectivity.startswith("8")
        merge = region_mode == REGION_MODES[1]

        combined = torch.zeros((B, H, W), dtype=torch.float32, device=device)
        individual = []
        info = []

        for b in range(B):
            binary_np = (mask[b] > threshold).cpu().numpy()
            if not binary_np.any():
                continue

            if merge:
                ys, xs = np.where(binary_np)
                boxes = [(xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, int(binary_np.sum()))]
            else:
                labels, n = _label_regions(binary_np, eight)
                boxes = _region_boxes(labels, n)

            for (x0, y0, x1, y1, area) in boxes:
                if area < min_area:
                    continue
                cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
                if mode == "circle_min":
                    rx = ry = min(rx, ry)
                elif mode == "circle_max":
                    rx = ry = max(rx, ry)
                rx = max(rx * scale, 0.5)
                ry = max(ry * scale, 0.5)

                patch = _ellipse_patch(H, W, cx, cy, rx, ry, feather, device)
                if patch is None:
                    continue
                py0, py1, px0, px1, alpha = patch

                combined[b, py0:py1, px0:px1] = torch.maximum(combined[b, py0:py1, px0:px1], alpha)
                single = torch.zeros((H, W), dtype=torch.float32, device=device)
                single[py0:py1, px0:px1] = alpha
                individual.append(single)
                info.append({
                    "batch": b,
                    "x": int(round(cx - rx)),
                    "y": int(round(cy - ry)),
                    "width": int(round(rx * 2)),
                    "height": int(round(ry * 2)),
                })

        if individual:
            individual_masks = torch.stack(individual, dim=0)
        else:
            individual_masks = torch.zeros((1, H, W), dtype=torch.float32, device=device)

        return (combined, individual_masks, json.dumps(info), len(info))


NODE_CLASS_MAPPINGS = {"MaskEllipser": MaskEllipser}
NODE_DISPLAY_NAME_MAPPINGS = {"MaskEllipser": "Mask Ellipser (Rect to Ellipse / Circle)"}
