"""PDF 压缩核心引擎 - 基于 PyMuPDF (fitz) 实现高保真与自适应压缩"""

import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import fitz


@dataclass
class CompressionResult:
    input_path: Path
    output_path: Path
    original_size: int
    compressed_size: int
    ratio: float  # 压缩减小百分比，如 65.2 表示减少了 65.2% 的体积
    elapsed_time: float
    status: str  # "SUCCESS", "SKIPPED_LARGER", "ERROR"
    error_message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == "SUCCESS"


# 预设模式配置
MODE_PRESETS: Dict[str, Dict] = {
    "balanced": {
        "dpi_threshold": 160,
        "dpi_target": 150,
        "quality": 75,
        "description": "平衡模式（推荐）：150 DPI / 质量 75，兼顾画质与体积，适合日常办公",
    },
    "light": {
        "dpi_threshold": 220,
        "dpi_target": 200,
        "quality": 85,
        "description": "轻度保真：200 DPI / 质量 85，接近无损画质，适合印刷或设计图",
    },
    "aggressive": {
        "dpi_threshold": 110,
        "dpi_target": 100,
        "quality": 55,
        "description": "极限压缩：100 DPI / 质量 55，最大幅度缩减体积，适合邮件或限制上传",
    },
    "lossless": {
        "dpi_threshold": 0,
        "dpi_target": 0,
        "quality": 0,
        "description": "纯无损：不修改图片，仅深度清理无效对象并压缩对象流",
    },
}


def format_size(size_bytes: int) -> str:
    """人性化格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class PDFCompressor:
    """PDF 压缩控制器"""

    def __init__(
        self,
        mode: str = "balanced",
        quality: Optional[int] = None,
        dpi_target: Optional[int] = None,
        dpi_threshold: Optional[int] = None,
        skip_if_larger: bool = True,
    ):
        self.mode = mode.lower() if mode else "balanced"
        if self.mode not in MODE_PRESETS and self.mode != "custom":
            raise ValueError(f"未知压缩模式: '{mode}'，可选: {list(MODE_PRESETS.keys())}")

        preset = MODE_PRESETS.get(self.mode, {})
        self.quality = quality if quality is not None else preset.get("quality", 75)
        self.dpi_target = (
            dpi_target if dpi_target is not None else preset.get("dpi_target", 150)
        )
        self.dpi_threshold = (
            dpi_threshold
            if dpi_threshold is not None
            else preset.get("dpi_threshold", 160)
        )
        self.skip_if_larger = skip_if_larger

        # 校验 DPI 参数关系
        if self.mode != "lossless" and self.dpi_target > 0:
            if self.dpi_threshold <= self.dpi_target:
                self.dpi_threshold = self.dpi_target + 10

    def compress_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        password: Optional[str] = None,
    ) -> CompressionResult:
        """压缩单个 PDF 文件

        :param input_path: 输入文件路径
        :param output_path: 输出文件路径（若为 None，则生成 原文件名_compressed.pdf）
        :param password: PDF 密码（如加密）
        :return: CompressionResult 压缩结果
        """
        start_time = time.time()
        in_p = Path(input_path).resolve()

        if not in_p.exists():
            return CompressionResult(
                input_path=in_p,
                output_path=Path(output_path) if output_path else in_p,
                original_size=0,
                compressed_size=0,
                ratio=0.0,
                elapsed_time=time.time() - start_time,
                status="ERROR",
                error_message=f"文件不存在: {in_p}",
            )

        if not in_p.suffix.lower() == ".pdf":
            return CompressionResult(
                input_path=in_p,
                output_path=Path(output_path) if output_path else in_p,
                original_size=in_p.stat().st_size,
                compressed_size=0,
                ratio=0.0,
                elapsed_time=time.time() - start_time,
                status="ERROR",
                error_message=f"不是 PDF 文件: {in_p}",
            )

        orig_size = in_p.stat().st_size

        # 确定输出文件路径
        if output_path is None:
            out_p = in_p.parent / f"{in_p.stem}_compressed.pdf"
        else:
            out_p = Path(output_path).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)

        # 使用临时文件进行安全写入，防止中途异常破坏原文件或输出文件
        temp_file = None
        try:
            doc = fitz.open(in_p)

            # 密码验证
            if doc.is_encrypted:
                if password:
                    if not doc.authenticate(password):
                        doc.close()
                        return CompressionResult(
                            input_path=in_p,
                            output_path=out_p,
                            original_size=orig_size,
                            compressed_size=0,
                            ratio=0.0,
                            elapsed_time=time.time() - start_time,
                            status="ERROR",
                            error_message="密码错误，无法解密 PDF",
                        )
                else:
                    doc.close()
                    return CompressionResult(
                        input_path=in_p,
                        output_path=out_p,
                        original_size=orig_size,
                        compressed_size=0,
                        ratio=0.0,
                        elapsed_time=time.time() - start_time,
                        status="ERROR",
                        error_message="PDF 受密码保护，请使用 --password 参数指定密码",
                    )

            # 执行图像重写（非 lossless 模式）
            if self.mode != "lossless" and self.quality > 0:
                doc.rewrite_images(
                    dpi_threshold=self.dpi_threshold,
                    dpi_target=self.dpi_target,
                    quality=self.quality,
                    lossy=True,
                    lossless=True,
                    bitonal=True,
                    color=True,
                    gray=True,
                )

            # 保存到临时文件
            temp_fd, temp_file_path = tempfile.mkstemp(
                suffix=".pdf", dir=str(out_p.parent)
            )
            os.close(temp_fd)
            temp_file = Path(temp_file_path)

            doc.save(
                temp_file,
                garbage=4,  # 最高级别无用对象清理并合并重复流
                deflate=True,  # 压缩未压缩的流
                clean=True,  # 规范化清理内容流
            )
            doc.close()

            new_size = temp_file.stat().st_size

            # 负优化熔断保护机制：如果压缩后反而变大
            if self.skip_if_larger and new_size >= orig_size:
                if temp_file.exists():
                    temp_file.unlink()

                # 如果输出路径与输入路径不同，复制原件过去；相同则保留原件
                if in_p != out_p:
                    shutil.copy2(in_p, out_p)

                return CompressionResult(
                    input_path=in_p,
                    output_path=out_p,
                    original_size=orig_size,
                    compressed_size=orig_size,
                    ratio=0.0,
                    elapsed_time=time.time() - start_time,
                    status="SKIPPED_LARGER",
                    error_message="文件已高度优化，进一步压缩无法减小体积，已保留原文件",
                )

            # 正常替换目标输出文件
            if out_p.exists():
                out_p.unlink()
            temp_file.rename(out_p)
            temp_file = None  # 标记已安全移动

            ratio = ((orig_size - new_size) / orig_size) * 100.0 if orig_size > 0 else 0.0

            return CompressionResult(
                input_path=in_p,
                output_path=out_p,
                original_size=orig_size,
                compressed_size=new_size,
                ratio=round(ratio, 2),
                elapsed_time=time.time() - start_time,
                status="SUCCESS",
            )

        except Exception as e:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return CompressionResult(
                input_path=in_p,
                output_path=out_p,
                original_size=orig_size,
                compressed_size=0,
                ratio=0.0,
                elapsed_time=time.time() - start_time,
                status="ERROR",
                error_message=str(e),
            )

    def compress_batch(
        self,
        files: List[Path],
        output_dir: Optional[Path] = None,
        replace_original: bool = False,
        progress_callback: Optional[Callable[[int, int, CompressionResult], None]] = None,
    ) -> List[CompressionResult]:
        """批量压缩文件列表"""
        results = []
        total = len(files)

        for idx, file_p in enumerate(files, start=1):
            if replace_original:
                out_p = file_p
            elif output_dir:
                out_p = output_dir / file_p.name
            else:
                out_p = None

            res = self.compress_file(file_p, out_p)
            results.append(res)

            if progress_callback:
                progress_callback(idx, total, res)

        return results
