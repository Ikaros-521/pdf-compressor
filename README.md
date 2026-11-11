# PDF 智能高效压缩工具 (Python / 跨平台 GUI 版)

轻量、快速、无冗余依赖的本地 PDF 压缩解决方案。基于底层 `PyMuPDF (fitz)` C 核心流优化与自适应图像降采样。提供**跨平台桌面图形界面 (GUI)**、**命令行 CLI**、**自动化文件夹监听**及 **Windows 拖拽一键压缩**，并支持 GitHub Actions 跨平台自动打包发版。

---

## 核心特性

- 🖥️ **跨平台简易 GUI**：原生桌面界面（Tkinter），支持文件多选、整目录添加、实时进度条与详细压缩日志，开箱即用。
- 🚀 **极速高效**：基于底层 MuPDF C 库，直接操作 PDF 内容流与对象结构，压缩 100MB+ 大文件仅需数秒。
- ⚖️ **平衡画质**：默认预设平衡模式（150 DPI / 质量 75），在肉眼无法分辨差异的前提下，将文件体积缩减 50% ~ 85%。
- 🛡️ **负优化熔断保护**：若原文件已被深度优化，再压缩体积无法缩小，工具将自动保留原文件并明确提示，杜绝“越压缩越大”。
- 🤖 **无人值守自动化**：自带 `watcher.py` 文件夹监控器，新 PDF 放入即自动压缩并自动归档原件。
- 🖱️ **Windows 拖拽支持**：支持将 PDF 文件或整个文件夹直接拖到 `compress_drop.bat` 图标上即时压缩。
- 📦 **自动打包发布 (CI/CD)**：内置 GitHub Actions，推送 Tag 自动跨平台打包 Windows、macOS、Linux 独立可执行文件并发布 Release。

---

## 快速使用

### 方式一：下载预编译可执行文件（推荐免安装）

请前往 [GitHub Releases](https://github.com/Ikaros-521/pdf-compressor/releases) 下载适合您操作系统的预编译独立程序包：
- **Windows**: `pdf-compressor-windows-x64.zip`（解压即可双击运行，无需安装 Python）
- **macOS**: `pdf-compressor-macos-arm64.zip`
- **Linux**: `pdf-compressor-linux-x86_64.tar.gz`

---

### 方式二：源码运行

#### 1. 环境依赖安装
确保已安装 Python 3.8+，并安装核心库：
```bash
pip install -r requirements.txt
```
*(主要依赖 `pymupdf` 和 `pillow`)*

#### 2. 启动桌面图形界面 (GUI)
- **Windows 用户**：直接双击运行 [`run_gui.bat`](run_gui.bat)
- **命令行启动**：
  ```bash
  python gui.py
  ```

#### 3. 命令行交互使用 (`cli.py`)
```bash
# 默认平衡模式压缩单个文件（输出为 原文件名_compressed.pdf）
python cli.py example.pdf

# 自定义输出路径
python cli.py example.pdf -o output/report_mini.pdf

# 批量压缩当前目录下所有的 PDF
python cli.py *.pdf -o ./output/

# 递归遍历所有子目录中的 PDF
python cli.py ./documents/ -o ./output/ -r

# 切换模式（balanced 平衡 / light 轻度 / aggressive 极限 / lossless 纯无损）
python cli.py report.pdf -m aggressive

# 自定义 DPI 和图像质量
python cli.py report.pdf --dpi 120 -q 65

# 原地覆盖原文件（若体积未缩小则不覆盖）
python cli.py report.pdf --replace
```

#### 4. 无人值守自动化文件夹监控 (`watcher.py`)
双击 [`start_watcher.bat`](start_watcher.bat) 或执行：
```bash
python watcher.py
```
- 将待压缩的 PDF 放入 `./watch_input/`
- 自动压缩输出至 `./watch_output/`，原文件自动归档至 `./watch_archive/`

#### 5. Windows 鼠标拖拽快捷模式 (`compress_drop.bat`)
选中任意一个或多个 PDF，直接拖到 `compress_drop.bat` 图标上方松开即可自动压缩。

---

## 自动打包与发版 (GitHub Actions)

项目已配置 `.github/workflows/release.yml` 自动化构建工作流：
1. **自动发版**：向仓库推送版本标签（例如 `v1.0.0`），GitHub Actions 将自动并行在 Windows、macOS 和 Linux 环境下拉取代码、构建单文件独立程序并发布到 GitHub Releases：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. **手动触发**：在 GitHub 仓库的 **Actions** 标签页中，选中 **Build and Release** 工作流，点击 **Run workflow** 即可随时手动触发全平台打包。

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。
