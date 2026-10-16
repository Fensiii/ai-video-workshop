# 特斯拉车型进化史（2D 动画）

1920×1080、60fps、无声，约 60 秒。车头朝右，锁定在画面中央，一直向右行驶。每次换代时旧车拆散成零件，在空中变形，再组装成下一代。

| 年份 | 标题 | 车型 | 场景 |
|---|---|---|---|
| 2008 | 第一款量产车 | Roadster | 车库 → 乡间公路 |
| 2012 | 豪华纯电轿车 | Model S | 黄昏高速 |
| 2015 | 鹰翼门 SUV | Model X | 黄昏高速 |
| 2017 | 走向大众 | Model 3 | 夜晚城市 |
| 2020 | 更大的空间 | Model Y | 夜晚城市 |
| 2023 | 不锈钢车身 | Cybertruck | 超级工厂 |
| 2024 | 自动驾驶出行 | Cybercab | 未来城市 |
| 2026 | 腾空 | 新一代 Roadster | 未来城市 → 实拍起飞 |

## 车型精度
- Model S / X / 3 / Y / Cybertruck：按参考侧面图描摹轮廓，再按官方长、高、轴距和前后悬分段映射，比例一比一。外观按首发年份。
- Roadster 2008：按官方尺寸（3946×1127mm，轴距 2352mm）绘制。
- Cybercab、新一代 Roadster：官方没有公布完整尺寸，按公开图片推算。

## 渲染
```
pip install skia-python numpy pillow
# 起飞实拍：裁剪、跟踪、镜像、慢放后的片段（见 footage.sh）
FOOTAGE=path/to/foot.mp4 python3 render.py out/tesla_evolution.mp4 --jobs 4
python3 render.py --still 3.0,10.5 out/      # 导出指定时间点的静帧
```

文件：`cars.py` 车型几何，`carrender.py` 车辆绘制与拆解组装，`scenes.py` 视差背景，`render.py` 时间线与输出，`footage.sh` 实拍素材处理。
