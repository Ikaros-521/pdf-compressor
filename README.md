# PDF 智能高效压缩工具 (Python 版)

轻量、快速、无冗余依赖的本地 PDF 压缩解决方案。基于底层 `PyMuPDF (fitz)` C 核心流优化与自适应图像降采样，支持单文件、通配符多文件、整目录批量、自动化文件夹监听及 Windows 鼠标拖拽一键压缩。

---

## 核心特性

- 🚀 **极速高效**：基于底层 MuPDF C 库，直接操作 PDF 内容流与对象结构，压缩 100MB+ 大文件仅需数秒。
- ⚖️ **平衡画质**：默认预设平衡模式（150 DPI / 质量 75），在肉眼无法分辨差异的前提下，将文件体积缩减 50% ~ 85%。
- 🛡️ **负优化熔断保护**：若原文件已被深度优化，再压缩体积无法缩小，工具将自动保留原文件并明确提示，杜绝“越压缩越大”。
- 🤖 **无人值守自动化**：自带 `watcher.py` 文件夹监控器，新 PDF 放入即自动压缩并自动归档原件。
- 🖱️ **Windows 拖拽支持**：支持将 PDF 文件或整个文件夹直接拖到 `compress_drop.bat` 图标上即时压缩。

---

## 快速上手

### 1. 环境依赖

确保已安装 Python 3.8+，并安装核心库：
```bash
pip install -r requirements.txt
```
*(主要依赖 `pymupdf` 和 `pillow`)*

---

### 2. 命令行使用方法 (`cli.py`)

#### 基础压缩（单文件）
```bash
# 默认平衡模式压缩，输出为 example_compressed.pdf
python cli.py example.pdf

# 自定义输出路径
python cli.py example.pdf -o output/report_mini.pdf
```

#### 批量压缩（目录与通配符）
```bash
# 批量压缩当前目录下所有的 PDF
python cli.py *.pdf -o ./output/

# 压缩整个 documents 目录到 output 目录
python cli.py ./documents/ -o ./output/

# 递归遍历所有子目录中的 PDF
python cli.py ./documents/ -o ./output/ -r
```

#### 压缩模式选择 (`-m / --mode`)
```bash
# 1. 平衡模式（默认）：兼顾清晰度与大幅缩小体积，适合日常办公、合同、课件
python cli.py report.pdf -m balanced

# 2. 轻度保真：200 DPI / 质量 85，接近无损，适合设计图纸或高清打印
python cli.py report.pdf -m light

# 3. 极限压缩：100 DPI / 质量 55，追求极小文件体积，适合邮件超额附件或限制上传
python cli.py report.pdf -m aggressive

# 4. 纯无损模式：不降低图片画质，仅清理无效对象和压缩流
python cli.py report.pdf -m lossless
```

#### 高级参数
```bash
# 自定义 DPI 和图像质量
python cli.py report.pdf --dpi 120 -q 65

# 原地覆盖原文件（若体积未缩小则不覆盖）
python cli.py report.pdf --replace

# 密码解密
python cli.py protected.pdf -p "123456"
```

---

### 3. 自动化文件夹监控 (`watcher.py`)

启动监控服务，实现无人值守自动压缩：
```bash
python watcher.py
```
默认工作流程：
1. 将待压缩的 PDF 放入 `./watch_input/`
2. 服务自动检测并完成压缩，输出至 `./watch_output/`
3. 原文件自动归档至 `./watch_archive/`

自定义监控目录：
```bash
python watcher.py -w "D:/Incoming_PDF" -o "D:/Compressed_PDF" -a "D:/Archive_PDF" -m balanced
```

---

### 4. Windows 快捷拖拽 (`compress_drop.bat`)

1. 在 Windows 资源管理器中选中任意一个或多个 PDF 文件。
2. 鼠标按住直接拖到 `compress_drop.bat` 图标上方松开。
3. 脚本自动启动控制台完成压缩并打印压缩对比报告。
*(提示：可右键 `compress_drop.bat` 创建快捷方式并放置在桌面或添加到系统的 "发送到 (SendTo)" 菜单中)*
