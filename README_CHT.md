# ComfyUI-MaskEllipser

[English](README.md) | [繁體中文](README_CHT.md)

一個小巧的 ComfyUI 自訂節點，可以**自動把方形、長方形（或任意形狀）的遮罩變成橢圓形或圓形**。節點會自行計算每個遮罩區域的外框（x、y、寬、高），並畫出對應的橢圓或圓，不需要手動輸入座標，也不必拉一堆節點。

## 功能特色

- **單一節點，免設定**：接上 `MASK`，輸出就是橢圓或圓形的 `MASK`。
- **每個區域各自獨立轉換**：遮罩中若有多個分開的方塊，每一個都會變成自己的橢圓或圓，而不是把全部包成一個巨大橢圓。
- **支援批次**：批次中的每一張遮罩都會處理。
- **橢圓或圓形**：可選內接橢圓，或以較短邊、較長邊為直徑的圓。
- **縮放與柔化**：可放大縮小結果並柔化邊緣。
- **額外輸出**：各區域獨立遮罩與外框資料（JSON），方便後續裁切、重繪、合成。
- 僅使用 PyTorch / NumPy。`scipy` 為選用，只用來加速區域標記。

## 安裝

### 使用 Git

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/<your-username>/ComfyUI-MaskEllipser.git
```

重新啟動 ComfyUI。（選用：執行 `pip install -r requirements.txt` 安裝 `scipy`。）

### 手動安裝

下載本專案的 ZIP，解壓縮到 `ComfyUI/custom_nodes/ComfyUI-MaskEllipser`，再重新啟動 ComfyUI。

## 使用方式

在畫布上雙擊，搜尋 **Mask Ellipser**，把遮罩接到 `mask` 輸入即可。節點位於 `mask` 分類下。

### 輸入

| 名稱 | 選項／範圍 | 說明 |
|------|-----------|------|
| `mask` | MASK | 輸入遮罩（單張或批次）。 |
| `shape` | `Ellipse (inscribed in bounding box)` / `Circle (shorter side)` / `Circle (longer side)` | 輸出形狀。圓形選項以區域的較短邊或較長邊作為直徑，並保持區域中心。 |
| `region_mode` | `Each region separately` / `Merge all into one` | 每個分離的區域各自轉換（預設），或把所有遮罩像素視為單一區域。 |
| `threshold` | 0.0 – 1.0（預設 0.5） | 大於此值的像素視為遮罩。 |
| `scale` | 0.1 – 5.0（預設 1.0） | 以中心為基準縮放結果。1.0 表示剛好內接於外框。 |
| `feather` | 0 – 1024 px（預設 0） | 邊緣柔化寬度，從形狀邊界向內漸層。0 為硬邊。 |
| `min_area` | ≥ 1（預設 1） | 忽略像素數小於此值的區域（可用來濾除雜點）。 |
| `connectivity` | `8-connected` / `4-connected` | 像素歸為同一區域的判定方式。8 連通會把斜角相鄰的像素視為同一區域。 |

### 輸出

| 名稱 | 類型 | 說明 |
|------|------|------|
| `mask` | MASK | 所有產生的橢圓／圓形合併後的遮罩，批次數量與輸入相同。 |
| `individual_masks` | MASK | 每個偵測到的區域各一張完整尺寸的遮罩（堆疊成批次）。若沒有任何區域，回傳一張空白遮罩。 |
| `bboxes` | STRING | 結果形狀外框的 JSON 清單，例如 `[{"batch": 0, "x": 20, "y": 20, "width": 80, "height": 40}]`。 |
| `count` | INT | 轉換的區域數量。 |

## 注意事項

- 相互接觸或重疊的區域會在標記時被視為同一個區域。請先將它們分開；若只是斜角相接，可改用 `4-connected`。
- 輸出的形狀若互相重疊，在 `mask` 中以逐像素取最大值合併。
- 小技巧：若只想轉換特定區域，可以只輸入包含該區域的遮罩，或在後續使用 `individual_masks`。

## 授權

MIT，詳見 [LICENSE](LICENSE)。
