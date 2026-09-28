# ComfyUI-MaskEllipser

[English](README.md) | [繁體中文](README_CHT.md)

A tiny ComfyUI custom node that turns **rectangular (or any-shaped) masks into ellipses or circles**, automatically. It measures each mask region's bounding box (x, y, width, height) and draws a matching ellipse or circle. No manual coordinates, no node spaghetti.

## Features

- **One node, zero setup**: plug in a `MASK`, get an elliptical / circular `MASK` back.
- **Each region is converted independently**: if your mask contains several separate rectangles, every one becomes its own ellipse or circle (not one giant ellipse around all of them).
- **Batch support**: works on every mask in a batch.
- **Ellipse or circle**: inscribed ellipse, or a circle based on the shorter or longer side.
- **Scale and feather**: grow/shrink the result and soften the edge.
- **Extra outputs**: per-region masks and bounding boxes (JSON) for cropping, inpainting, compositing, etc.
- Pure PyTorch/NumPy. `scipy` is optional and only speeds up region labeling.

## Installation

### Git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/K0KU20/ComfyUI-MaskEllipser.git
```

Restart ComfyUI. (Optional: `pip install -r requirements.txt` for `scipy`.)

### Manual

Download this repository as a ZIP and extract it into `ComfyUI/custom_nodes/ComfyUI-MaskEllipser`, then restart ComfyUI.

## Usage

Double-click the canvas, search for **Mask Ellipser**, and connect your mask to the `mask` input. The node is found under the `mask` category.

### Inputs

| Name | Options / Range | Description |
|------|-----------------|-------------|
| `mask` | MASK | Input mask (single or batch). |
| `shape` | `Ellipse (inscribed in bounding box)` / `Circle (shorter side)` / `Circle (longer side)` | Output shape. The circle options use the region's shorter or longer side as the diameter and keep the region's center. |
| `region_mode` | `Each region separately` / `Merge all into one` | Convert every separate region on its own (default), or treat all masked pixels as one region. |
| `threshold` | 0.0 – 1.0 (default 0.5) | Pixels above this value count as masked. |
| `scale` | 0.1 – 5.0 (default 1.0) | Scales the resulting shape around its center. 1.0 = exactly inscribed in the bounding box. |
| `feather` | 0 – 1024 px (default 0) | Soft edge width, fading inward from the shape boundary. 0 = hard edge. |
| `min_area` | ≥ 1 (default 1) | Ignore regions smaller than this many pixels (useful to drop noise). |
| `connectivity` | `8-connected` / `4-connected` | How pixels are grouped into a region. Diagonal neighbors join a region only with 8-connected. |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| `mask` | MASK | All generated ellipses/circles combined, same batch size as the input. |
| `individual_masks` | MASK | One full-size mask per detected region (stacked as a batch). Returns a single empty mask if nothing is found. |
| `bboxes` | STRING | JSON list of the resulting shapes' bounding boxes, e.g. `[{"batch": 0, "x": 20, "y": 20, "width": 80, "height": 40}]`. |
| `count` | INT | Number of regions converted. |

## Notes

- Regions that touch or overlap are merged by the labeling step and treated as one region. Separate them first, or use `4-connected` if they only touch diagonally.
- Overlapping output shapes are combined with a per-pixel maximum in `mask`.
- Tip: to convert only a specific region, feed a mask that contains just that region, or use `individual_masks` downstream.

## License

MIT. See [LICENSE](LICENSE).
