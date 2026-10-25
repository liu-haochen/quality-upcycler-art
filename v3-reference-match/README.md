# v3 参考图高相似度静态与连续状态机动画

参考：`../v3/image.png`（用户提供的环形工业机器）。本目录不是对原图做贴图、描边或抠图，而是用 Blender 程序化重建一台同一视觉语言的机器，并输出静态展示渲染、待机动画和加工动画。

## 已完成

- 三组机械臂各自拥有独立的圆形轨道 carriage，沿机身内圈做不同方向、不同相位的短弧圆周运动；到各自工位后停驻，再展开肘关节做下压/剪切。
- 每组机械臂保留独立肩/肘/腕层级；中间肘关节在 carousel 换位时折叠避让、在停驻时大幅展开下压，真正参与循环。加工台改为小幅往复剪切，不再与 carousel 同时 360° 旋转。
- 中央工作台加装旋转层级，在两次加工之间做 ±13° 分度摆动，并在循环末尾回到零位，避免 32 帧循环发生可见闪跳。
- 五组内外齿轮在加工循环内旋转。
- 加工腔任务灯随两次下压脉冲明暗变化；待机状态完全熄灭。
- 待机时指示灯切为红色且不发光；加工时指示灯切为绿色并自发光。
- 打光改为符合 Factorio 视觉习惯的屏幕左上主光：太阳/主光从左侧照入，右侧补光压低，阴影落在右侧。
- 输出静态安全待机姿态、32 帧加工动画、32 帧加工专用 additive glow 图层、独立真实投影、图标和 Factorio `graphics_set`。
- 使用 `working_visualisations.states` 把待机/加工拆成视觉状态：加工结束不会立刻切到另一套机械姿态；机身层在当前视觉状态里继续走完，glow 和实体工作灯以 `fadeout=true` 先熄灭，最后落到与加工安全姿态完全一致的静态待机图，避免位置闪跳。
- 新增 `quality-upcycler-idle-static.png`：直接取加工循环最后一帧的安全姿态，用待机材质重新渲染，因此工作→待机只改变发光材质。

最终静态展示图由 `quality-upcycler-reference-match-animated.blend` 的第 113 帧（左臂下压、转台分度中）重渲；建模基础文件保留原尺寸手臂，便于对比。

## 成果文件

| 文件 | 内容 |
| --- | --- |
| `quality-upcycler-reference-match.png` | 静态展示渲染，2000×700，白底、右向投影 |
| `quality-upcycler-reference-match-small.png` | 1000×350 静态对照尺寸 |
| `quality-upcycler-reference-match-square.png` | 1000×1000 透明背景近景 |
| `quality-upcycler-reference-match.blend` | 静态建模基础文件（保留原手臂尺寸） |
| `quality-upcycler-reference-match-animated.blend` | 最终动画场景：缩臂、机械臂层级、转台、齿轮和灯光关键帧 |
| `idle-vs-working.png` | 待机/加工姿态对照 |
| `work-to-idle-hold-compare.png` | 加工最后一帧与静态待机同一姿态、仅灯光材质不同 |
| `animation-pose-preview.png` | 12 个待机/加工关键姿态检查图 |
| `footprint-idle-preview.png` | 待机状态占地与投影预览 |
| `footprint-work-preview.png` | 加工状态占地与投影预览 |
| `quality-upcycler-glow-animation.png` | 加工专用 additive glow Atlas；包含绿色指示灯、琥珀色灯窗和两段环形流光 |
| `quality-upcycler-idle-static.png` | 与加工最后一帧同一安全姿态的静态待机帧；仅使用待机材质 |
| `night-idle-vs-working.png` | 模拟夜晚压暗后的待机/加工光照对照 |
| `quality-upcycler-working.gif` | 加工循环 GIF |
| `quality-upcycler-idle.gif` | 待机循环 GIF |
| `installed-graphics/` | 可直接放入 `mod/graphics` 的加工 Atlas、静态待机帧、加工 glow Atlas、阴影、图标和状态机 `animation.lua` |
| `build_animation.py` | 缩臂、建立肩/肘/腕层级、转台与齿轮旋转、写入待机/加工关键帧 |
| `render_animation.py` | 切换待机/加工材质状态，渲染 32 帧加工、32 帧加工 glow 图层和 1 帧静态安全待机姿态 |
| `render_animation_shadow.py` | 投影生成 480×480 独立阴影 |
| `render_static_from_animated.py` | 从最终动画场景第 113 帧重渲静态展示图 |
| `pack_animation.py` | 打包加工 Atlas、静态待机帧、图标、GIF、预览与状态机 `animation.lua` |

## 动画结构

| 状态 | 帧数 | animation_speed | 内容 |
| --- | ---: | ---: | --- |
| 待机 `idle_animation` | 32 | 0.12 | 机械臂低幅伺服呼吸，工作台静止；任务灯/屏幕关闭，指示灯为红色非发光 |
| 加工 `animation` | 32 | 0.50 | 三臂各自的 carriage 沿内圈做独立短弧圆周运动，到工位后伸展肘关节下压/剪切；工作台小幅往复，齿轮旋转，混合灯光与长线流光 |

- 动画帧尺寸：`320×320`，`line_length=8`。
- 游戏缩放：`scale=0.5`，与项目现有机器资产一致。
- 可见范围：约 `125.5×112.5` 游戏像素，允许比 3×3 碰撞箱适度外伸。
- 合成偏移：`util.by_pixel(4.0, -2.75)`。
- 独立阴影：`480×480` 真实几何投影，工作时和待机时复用同一静态投影层。
- 夜间加工：基础动画会被 Factorio 夜色压暗；加工动画层中的 additive glow Atlas 保持混合状态灯、青色屏幕、琥珀色灯窗和环形流光在黑夜中明亮，同时由 `working_visualisations` 提供暖色主工作光和极低强度绿色辅光。
- 待机红色指示灯：使用非自发光红色材质，只在白天环境光下可见；进入加工状态后替换为绿色自发光材质。
- 打光方向：主光/太阳位于画面左上方，右侧只保留低强度补光，阴影朝右。
- 阴影：按截图蓝箭头校准为**右向近水平投影**；投影偏移为 `x + 1.15z / y + 0.40z`，最终 alpha 为 **0.70**，从 3×3 机身向右延伸约半格到一格。
- 环境光：提高世界环境光、右侧冷补光和顶部柔光，并新增左下前方冷色 fill；机械臂和机身侧面不再只靠顶光，暗部结构更清楚。
- 流光：外圈顶部只保留一段长线流光，每 32 帧完成一整圈；前段慢、后段逐级加速，颜色依次经过 normal 银白 → uncommon 绿 → rare 蓝 → epic 紫 → legendary 橙金，最后快速回到银白以保证循环无缝。
- 灯光可读性：提高 Blender 环境曝光、右侧补光和工作腔任务灯能量；glow Atlas 的 bloom 半径收紧，避免相邻小灯颜色糊成一团。
- 高端配色：机身从暖橄榄/褐色改为冷蓝灰与深青灰铸件，外露机械臂和服务管改为拉丝黄铜/铜色，保留少量锈蚀、红色警告件和绿色品质指示灯。
- 四个顶部品质模块改为中性金属舱，只保留低饱和的小面积品质识别窗：uncommon 绿、rare 蓝、epic 紫、legendary 橙金；待机低亮，加工时柔和点亮。
- 加工 `animation.layers` 直接叠加 `quality-upcycler-glow-animation.png`，使用 `draw_as_glow=true` 和 additive 混合；glow 与机身动画共用同一 32 帧栈，避免两件物品切换时出现错相位闪烁。
- glow 图层不是手工把光斑画在机器上；它是 Cycles 单独渲染的 emission pass。
- 渲染 glow 时把所有非发光几何设为 Holdout，机械臂、外圈、屏幕分隔条和机身会真实遮挡背后的光；左前减速齿轮也向镜头平移 0.19 并缩小到 86%，避免与左侧服务盒和辅助电机接触。
- `working_visualisations` 以**暖色加工主光**为主，绿色只是一盏低强度状态辅光；两盏灯都设置 `fadeout=true`，避免整机被照成绿色。
- 状态灯改为两格分段模块，绿色、暖琥珀和红色错开；原青蓝大屏改为低饱和青绿工业状态矩阵，增加金属格栅肋条并降低亮度，减少消费电子 UI 感。
- 加工动画首帧与末帧的机械臂姿态、任务灯能量完全对齐；循环重启时不会出现额外暗帧。
- `states` 只有 `idle` 与 `working` 两个视觉状态；`working` 的 body layers 设置 `always_draw=true` 和 `draw_in_states={"working"}`，`duration=32` 与 32 帧动画周期一致；加工中断时当前视觉状态先走完，再回到静态安全姿态。
- glow 层和两盏工作灯均 `fadeout=true`；停机时先熄灭灯光，机身只继续机械动作，不再重新点亮。
- `idle_animation` 使用 1 帧静态安全姿态，因此从加工结束到待机不会发生机械臂位置跳变，视觉差异只剩发光材质。
- `reset_animation_when_frozen=true`，机器断电/冻结后回到状态机起点。

加工动画按自身 32 帧速度独立循环，不强行绑定配方进度；此前每件物品之间的闪帧来自 `control.lua` 强制停机一 tick，现已改为完成一件后继续运行，只在无输入或输出满时停机。

## 生成与打包

在项目根目录执行：

```powershell
# 1. 生成静态模型和静态高清渲染
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python art/v3-reference-match/build_reference_match.py
python art/v3-reference-match/polish_render.py
python art/v3-reference-match/make_comparison.py

# 2. 建立动画层级与关键帧（同时把机械臂缩到 86%）
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python art/v3-reference-match/build_animation.py

# 2b. 从最终动画场景输出静态展示渲染
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python art/v3-reference-match/render_static_from_animated.py
python art/v3-reference-match/polish_render.py
python art/v3-reference-match/make_comparison.py

# 3. 渲染 32 帧待机 + 32 帧加工
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python art/v3-reference-match/render_animation.py

# 4. 生成真实地面投影
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python art/v3-reference-match/render_animation_shadow.py

# 5. 打包 Atlas、GIF、预览和 animation.lua
python art/v3-reference-match/pack_animation.py
```

把 `installed-graphics/` 内容复制到 `mod/graphics/` 后运行 `install.ps1`，游戏重启即可加载双状态动画。

渲染脚本已配置 **Cycles OptiX**，使用 RTX 4060 Laptop GPU；动画帧按 idle/work/glow 三个状态批量渲染，避免原先逐帧渲染时每帧重复加载 GPU kernel。

## 游戏接入状态

- `mod/graphics/animation.lua` 已替换为 `idle` / `working` 视觉状态机定义。
- `mod/graphics/` 已包含 `quality-upcycler-animation.png`、`quality-upcycler-idle-animation.png`、`quality-upcycler-glow-animation.png`、`quality-upcycler-shadow.png` 和新图标。
- `animation.lua` 把 glow 图层直接放进加工动画 layers，`working_visualisations` 提供带 `fadeout` 的暖色主工作光和低强度绿色辅光；待机不绘制 glow 层。
- 加工动画按自身 `animation_speed = 0.50` 独立循环；`animation_progress` 已移除，避免引擎在每个配方完成点重置帧相位。视觉状态 `working` 的 `duration = 32` 表示一个 32 帧加工周期；配合 `animation_speed = 0.50`，视觉状态正好在一个完整周期后切换，不会额外拉长成两倍。
- `control.lua` 已修复逐件闪烁源：以前每完成一件物品会强制 `disabled_by_script = true` 一 tick，使机器掉回 idle 动画；现在完成一件后保持启用，只在输出满/无输入时停机。
- `mod/data.lua` 仍通过 `machine.graphics_set=require("graphics.animation")` 加载，不需要改原型逻辑。
- 已用隔离 Factorio 地图跑完 9060 tick 基准；`upcycler-buffer.json` 与 `upcycler-report.json` 均有正常产出。该验证覆盖加载、脚本运行与出料，不是完整的逐帧视觉验货。
- `animation.lua` 的 `states`、`draw_in_states`、`always_draw`、`fadeout`、`draw_as_glow` 和两盏工作灯已通过 Factorio 数据阶段加载验证。
- 安装脚本已执行，当前游戏 mods 目录中的 `quality-upcycler_0.1.0` 已更新为本轮动画资源。

## 备份

改动前的暖色工业配色完整保存在 `../v3-reference-match-warm-industrial-backup/`，其中包含旧版 Blender 文件、脚本、预览、`installed-graphics/`，以及当时安装的 `mod-graphics-snapshot/`。

双段暖金流光、旧版状态灯布局和旧版渲染脚本完整保存在 ../v3-reference-match-two-comet-backup/，包含 Blender 场景、动画帧、Atlas、预览、mod-source-snapshot/ 和 installed-game-graphics-snapshot/。

加入 carousel 之前的版本完整保存在 ../v3-reference-match-pre-carousel-backup/，包含单段加速流光、Holdout glow、齿轮避让和旧的三臂异步动作。

顶部品质模块、右下状态矩阵和左下补光精修之前的版本完整保存在 ../v3-reference-match-pre-refinement-backup/。

引入视觉状态机之前的双状态动画完整保存在 ../v3-reference-match-pre-state-machine-backup/。

## 限制

- 这是静态视觉研究转成的游戏资产，不声称与参考图逐像素一致。
- 投影层是静态几何投影；动画中的机械臂、齿轮和转台会使用同一个静态阴影，不逐帧重算。
- 三条机械臂现在各自沿内圈做独立短弧往复；不再共用一个转盘，避免出现整圈同步旋转的感觉。加工台改为小幅往复剪切。
- The working animation runs on its own 32-frame loop and is intentionally independent of recipe progress. The old one-tick idle flash was fixed in control.lua.
- 参考图来源与再发布权利仍未确认。


























