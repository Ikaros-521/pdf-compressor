"""PDF 智能压缩桌面版 (跨平台简易 GUI)
基于 Python 原生 Tkinter 开发，支持多文件、整目录批量压缩与多档参数配置。
"""

import os
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import List, Optional

from compressor import MODE_PRESETS, PDFCompressor, format_size


class PDFCompressorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PDF 智能压缩工具 v1.0")
        self.root.geometry("760x640")
        self.root.minsize(680, 520)

        # 状态变量
        self.selected_files: List[Path] = []
        self.is_compressing = False
        self.should_stop = False

        self._init_style()
        self._build_ui()

    def _init_style(self):
        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        # 优先使用现代原生主题
        if "vista" in available_themes and sys.platform == "win32":
            self.style.theme_use("vista")
        elif "clam" in available_themes:
            self.style.theme_use("clam")

        self.style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 顶部：文件选择与列表区域
        file_frame = ttk.LabelFrame(main_frame, text="待压缩 PDF 文件列表", padding="8")
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        btn_box = ttk.Frame(file_frame)
        btn_box.pack(fill=tk.X, pady=(0, 6))

        self.btn_add_files = ttk.Button(btn_box, text="➕ 添加 PDF 文件...", command=self._add_files)
        self.btn_add_files.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_add_dir = ttk.Button(btn_box, text="📁 添加文件夹...", command=self._add_directory)
        self.btn_add_dir.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = ttk.Button(btn_box, text="🗑️ 清空列表", command=self._clear_files)
        self.btn_clear.pack(side=tk.LEFT)

        self.lbl_count = ttk.Label(btn_box, text="共 0 个文件", foreground="#555555")
        self.lbl_count.pack(side=tk.RIGHT)

        # Treeview 展示列表
        tree_scroll = ttk.Scrollbar(file_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            file_frame,
            columns=("name", "size", "status"),
            show="headings",
            height=6,
            yscrollcommand=tree_scroll.set,
        )
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("name", text="文件路径 / 名称")
        self.tree.heading("size", text="原始大小")
        self.tree.heading("status", text="状态")

        self.tree.column("name", width=420, anchor=tk.W)
        self.tree.column("size", width=100, anchor=tk.E)
        self.tree.column("status", width=120, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 2. 中部：压缩配置与输出配置区域
        config_frame = ttk.LabelFrame(main_frame, text="压缩模式与输出设置", padding="8")
        config_frame.pack(fill=tk.X, pady=(0, 8))

        # 模式选择
        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(row1, text="压缩预设:").pack(side=tk.LEFT, padx=(0, 8))
        self.mode_var = tk.StringVar(value="balanced")
        self.mode_combo = ttk.Combobox(
            row1,
            textvariable=self.mode_var,
            values=[
                "balanced - 平衡模式（推荐，兼顾画质与体积）",
                "light - 轻度保真（200 DPI，接近无损）",
                "aggressive - 极限压缩（100 DPI，超小体积）",
                "lossless - 纯无损模式（仅优化流与对象）",
                "custom - 自定义参数",
            ],
            state="readonly",
            width=42,
        )
        self.mode_combo.pack(side=tk.LEFT, padx=(0, 16))
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # 自定义参数控件
        self.custom_box = ttk.Frame(row1)
        self.custom_box.pack(side=tk.LEFT)

        ttk.Label(self.custom_box, text="DPI:").pack(side=tk.LEFT, padx=(4, 2))
        self.dpi_var = tk.IntVar(value=150)
        self.dpi_spin = ttk.Spinbox(
            self.custom_box, from_=50, to=300, increment=10, textvariable=self.dpi_var, width=5, state="disabled"
        )
        self.dpi_spin.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(self.custom_box, text="质量:").pack(side=tk.LEFT, padx=(4, 2))
        self.quality_var = tk.IntVar(value=75)
        self.quality_spin = ttk.Spinbox(
            self.custom_box, from_=10, to=100, increment=5, textvariable=self.quality_var, width=5, state="disabled"
        )
        self.quality_spin.pack(side=tk.LEFT)

        # 输出路径选项
        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X)

        self.out_type_var = tk.StringVar(value="same_dir")
        r_same = ttk.Radiobutton(
            row2,
            text="同目录下生成 *_compressed.pdf",
            value="same_dir",
            variable=self.out_type_var,
            command=self._toggle_output_dir,
        )
        r_same.pack(side=tk.LEFT, padx=(0, 16))

        r_custom = ttk.Radiobutton(
            row2,
            text="输出到指定文件夹:",
            value="custom_dir",
            variable=self.out_type_var,
            command=self._toggle_output_dir,
        )
        r_custom.pack(side=tk.LEFT, padx=(0, 6))

        self.out_dir_var = tk.StringVar()
        self.out_dir_entry = ttk.Entry(row2, textvariable=self.out_dir_var, width=32, state="disabled")
        self.out_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_browse_out = ttk.Button(row2, text="浏览...", command=self._choose_output_dir, state="disabled")
        self.btn_browse_out.pack(side=tk.LEFT)

        # 3. 执行按钮与进度条
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_start = ttk.Button(
            action_frame, text="🚀 开始压缩", style="Action.TButton", command=self._start_compression
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8), ipadx=10, ipady=3)

        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.lbl_status = ttk.Label(action_frame, text="就绪", foreground="#333333")
        self.lbl_status.pack(side=tk.RIGHT)

        # 4. 底部实时日志展示区域
        log_frame = ttk.LabelFrame(main_frame, text="压缩处理日志", padding="6")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = ScrolledText(log_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("SUCCESS", foreground="#2e7d32")
        self.log_text.tag_config("INFO", foreground="#1565c0")
        self.log_text.tag_config("WARN", foreground="#e65100")
        self.log_text.tag_config("ERROR", foreground="#c62828")

        self._log("欢迎使用 PDF 智能压缩工具！请添加待处理的 PDF 文件或文件夹。", "INFO")

    def _log(self, message: str, tag: str = "INFO"):
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n", tag)
        self.log_text.see(tk.END)

    def _on_mode_change(self, event=None):
        raw_val = self.mode_var.get()
        mode_key = raw_val.split(" - ")[0].strip()

        if mode_key == "custom":
            self.dpi_spin.config(state="normal")
            self.quality_spin.config(state="normal")
        else:
            self.dpi_spin.config(state="disabled")
            self.quality_spin.config(state="disabled")
            preset = MODE_PRESETS.get(mode_key, {})
            if preset.get("dpi_target"):
                self.dpi_var.set(preset["dpi_target"])
            if preset.get("quality"):
                self.quality_var.set(preset["quality"])

    def _toggle_output_dir(self):
        is_custom = self.out_type_var.get() == "custom_dir"
        state = "normal" if is_custom else "disabled"
        self.out_dir_entry.config(state=state)
        self.btn_browse_out.config(state=state)

    def _choose_output_dir(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.out_dir_var.set(d)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择待压缩的 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if not paths:
            return

        new_count = 0
        for p in paths:
            fp = Path(p).resolve()
            if fp not in self.selected_files:
                self.selected_files.append(fp)
                self.tree.insert(
                    "",
                    tk.END,
                    iid=str(fp),
                    values=(fp.name, format_size(fp.stat().st_size), "等待处理"),
                )
                new_count += 1

        self.lbl_count.config(text=f"共 {len(self.selected_files)} 个文件")
        self._log(f"添加了 {new_count} 个 PDF 文件。", "INFO")

    def _add_directory(self):
        d = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if not d:
            return

        dir_path = Path(d).resolve()
        pdf_list = list(dir_path.glob("*.pdf"))
        new_count = 0
        for fp in pdf_list:
            if fp not in self.selected_files:
                self.selected_files.append(fp)
                self.tree.insert(
                    "",
                    tk.END,
                    iid=str(fp),
                    values=(fp.name, format_size(fp.stat().st_size), "等待处理"),
                )
                new_count += 1

        self.lbl_count.config(text=f"共 {len(self.selected_files)} 个文件")
        self._log(f"从目录 '{dir_path.name}' 中扫描并添加了 {new_count} 个 PDF 文件。", "INFO")

    def _clear_files(self):
        if self.is_compressing:
            return
        self.selected_files.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_count.config(text="共 0 个文件")
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="已清空")

    def _start_compression(self):
        if not self.selected_files:
            messagebox.showwarning("提示", "请先添加至少一个待压缩的 PDF 文件！")
            return

        if self.out_type_var.get() == "custom_dir" and not self.out_dir_var.get().strip():
            messagebox.showwarning("提示", "请指定输出文件夹路径！")
            return

        self.is_compressing = True
        self.btn_start.config(state="disabled")
        self.btn_add_files.config(state="disabled")
        self.btn_add_dir.config(state="disabled")
        self.btn_clear.config(state="disabled")
        self.progress_bar["maximum"] = len(self.selected_files)
        self.progress_bar["value"] = 0

        # 获取配置
        raw_val = self.mode_var.get()
        mode_key = raw_val.split(" - ")[0].strip()
        custom_dpi = self.dpi_var.get() if mode_key == "custom" else None
        custom_q = self.quality_var.get() if mode_key == "custom" else None
        out_dir = (
            Path(self.out_dir_var.get().strip())
            if self.out_type_var.get() == "custom_dir"
            else None
        )

        threading.Thread(
            target=self._worker_thread,
            args=(mode_key, custom_q, custom_dpi, out_dir),
            daemon=True,
        ).start()

    def _worker_thread(
        self,
        mode: str,
        quality: Optional[int],
        dpi: Optional[int],
        out_dir: Optional[Path],
    ):
        compressor = PDFCompressor(
            mode=mode,
            quality=quality,
            dpi_target=dpi,
            skip_if_larger=True,
        )

        total = len(self.selected_files)
        saved_bytes_all = 0
        orig_bytes_all = 0
        success_count = 0

        for idx, fpath in enumerate(self.selected_files, start=1):
            self.root.after(
                0,
                lambda i=idx, n=fpath.name: self.lbl_status.config(
                    text=f"正在压缩 ({i}/{total}): {n}"
                ),
            )
            self.root.after(
                0,
                lambda p=str(fpath): self.tree.set(p, "status", "处理中..."),
            )

            # 确定输出文件路径
            if out_dir:
                out_p = out_dir / fpath.name
            else:
                out_p = None

            res = compressor.compress_file(fpath, out_p)
            orig_bytes_all += res.original_size

            # 回调 UI
            if res.status == "SUCCESS":
                success_count += 1
                saved = res.original_size - res.compressed_size
                saved_bytes_all += saved
                status_str = f"完成 (-{res.ratio}%)"
                log_str = (
                    f"✔ {fpath.name} 压缩成功! "
                    f"({format_size(res.original_size)} -> {format_size(res.compressed_size)}, "
                    f"减少 {res.ratio}%, 耗时 {res.elapsed_time:.2f}s)"
                )
                tag = "SUCCESS"
            elif res.status == "SKIPPED_LARGER":
                status_str = "已最优(保留原样)"
                log_str = f"⚠ {fpath.name} 无法进一步压缩，已保留原文件。"
                tag = "WARN"
            else:
                status_str = "失败"
                log_str = f"✖ {fpath.name} 处理失败: {res.error_message}"
                tag = "ERROR"

            self.root.after(0, lambda p=str(fpath), s=status_str: self.tree.set(p, "status", s))
            self.root.after(0, lambda m=log_str, t=tag: self._log(m, t))
            self.root.after(0, lambda v=idx: self.progress_bar.configure(value=v))

        # 完成后状态重置
        total_ratio = (
            ((saved_bytes_all) / orig_bytes_all * 100.0) if orig_bytes_all > 0 else 0.0
        )
        summary_msg = (
            f"所有文件压缩处理完成！\n"
            f"成功: {success_count}/{total} 个\n"
            f"累计节省空间: {format_size(saved_bytes_all)} (总体缩减 {total_ratio:.1f}%)"
        )

        def _finish():
            self.is_compressing = False
            self.btn_start.config(state="normal")
            self.btn_add_files.config(state="normal")
            self.btn_add_dir.config(state="normal")
            self.btn_clear.config(state="normal")
            self.lbl_status.config(text="全部处理完成")
            self._log("=" * 50, "INFO")
            self._log(summary_msg.replace("\n", " | "), "SUCCESS")
            messagebox.showinfo("处理完成", summary_msg)

        self.root.after(0, _finish)


def main():
    root = tk.Tk()
    app = PDFCompressorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
