# Quality Upcycler Art

这是品质转化机的 Blender 美术源文件与静态资产仓库，和可运行 mod 的发布仓库分开。

## 内容

- `v3-reference-match/`：最终采用的环形品质机 Blender 场景、构建/渲染/打包脚本、预览图、GIF、最终贴图 Atlas。
- `reference/image.png`：用户提供的参考图。

`animation-frames/` 是从 Blender 重新生成的中间帧，不进入 Git；需要时运行渲染脚本重建。

## 构建

在本目录下：

```powershell
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python v3-reference-match/build_animation.py
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python v3-reference-match/render_animation.py
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --background --factory-startup --python v3-reference-match/render_animation_shadow.py
python v3-reference-match/pack_animation.py
```

最终 `v3-reference-match/installed-graphics/` 里的 PNG 和 `animation.lua` 对应发布仓库中的 `mod/graphics/`。

大文件保留普通 Git 二进制对象；单个文件都低于 GitHub 的 100 MB 限制。若后续资产继续增大，可再迁移到 Git LFS。

## 相关仓库

- 可运行 mod：`quality-upcycler`
- 性能实验：`quality-upcycler-experiments`

