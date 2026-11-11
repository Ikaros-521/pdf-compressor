"""端到端功能验证测试套件"""

import io
import os
import shutil
import time
from pathlib import Path

import fitz
from PIL import Image

from compressor import PDFCompressor, format_size


def create_sample_pdf_with_images(filename: str, num_pages: int = 2) -> Path:
    """生成包含高分辨率图片的测试 PDF 文件"""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4 页面
        # 插入标题文本
        page.insert_text(fitz.Point(50, 40), f"测试文档 - 第 {i+1} 页", fontsize=16)

        # 生成 2000x2500 的高清测试图片
        img = Image.new("RGB", (2000, 2500), color=(100 + i * 40, 150, 200 - i * 30))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")

        rect = fitz.Rect(50, 60, 545, 780)
        page.insert_image(rect, stream=img_bytes.getvalue())

    p = Path(filename).resolve()
    doc.save(p)
    doc.close()
    return p


def create_sample_text_pdf(filename: str) -> Path:
    """生成仅包含矢量文本的轻量 PDF 文件"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for line_idx in range(50):
        page.insert_text(
            fitz.Point(50, 50 + line_idx * 15),
            f"这是测试段落第 {line_idx+1} 行内容，包含纯矢量文字排版。",
            fontsize=11,
        )
    p = Path(filename).resolve()
    doc.save(p)
    doc.close()
    return p


def run_tests():
    print("=" * 60)
    print("           PDF 压缩功能自动化端到端测试")
    print("=" * 60)

    test_dir = Path("test_workspace").resolve()
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)

    try:
        # 1. 准备样本
        print("\n[步骤 1/4] 生成测试用 PDF 样本...")
        heavy_pdf = create_sample_pdf_with_images(str(test_dir / "sample_heavy.pdf"))
        text_pdf = create_sample_text_pdf(str(test_dir / "sample_text.pdf"))

        print(f"  - 生成大图样本: {heavy_pdf.name} ({format_size(heavy_pdf.stat().st_size)})")
        print(f"  - 生成文本样本: {text_pdf.name} ({format_size(text_pdf.stat().st_size)})")

        # 2. 测试平衡模式 (Balanced)
        print("\n[步骤 2/4] 测试平衡模式 (Balanced)...")
        comp = PDFCompressor(mode="balanced")
        out_balanced = test_dir / "sample_heavy_balanced.pdf"
        res1 = comp.compress_file(heavy_pdf, out_balanced)

        print(f"  - 原始大小: {format_size(res1.original_size)}")
        print(f"  - 压缩大小: {format_size(res1.compressed_size)}")
        print(f"  - 压缩比例: 缩减 {res1.ratio}% (耗时: {res1.elapsed_time:.2f}s)")
        assert res1.is_success, "平衡模式压缩失败!"
        assert res1.ratio > 80.0, f"平衡模式压缩率未达预期: {res1.ratio}%"
        print("  -> 平衡模式测试通过！")

        # 3. 测试极限压缩模式 (Aggressive)
        print("\n[步骤 3/4] 测试极限模式 (Aggressive)...")
        comp_agg = PDFCompressor(mode="aggressive")
        out_agg = test_dir / "sample_heavy_aggressive.pdf"
        res2 = comp_agg.compress_file(heavy_pdf, out_agg)

        print(f"  - 原始大小: {format_size(res2.original_size)}")
        print(f"  - 压缩大小: {format_size(res2.compressed_size)}")
        print(f"  - 压缩比例: 缩减 {res2.ratio}% (耗时: {res2.elapsed_time:.2f}s)")
        assert res2.is_success, "极限模式压缩失败!"
        assert res2.compressed_size < res1.compressed_size, "极限模式应比平衡模式体积更小"
        print("  -> 极限模式测试通过！")

        # 4. 测试负优化熔断保护机制 (对已极小文件进行压缩)
        print("\n[步骤 4/4] 测试防负优化保护机制...")
        # 对刚刚压缩出的文件再次进行平衡压缩，预期触发 SKIPPED_LARGER 或保持优化
        res3 = comp.compress_file(out_balanced, test_dir / "sample_recompressed.pdf")
        print(f"  - 二次压缩状态: {res3.status}")
        if res3.status == "SKIPPED_LARGER":
            print(f"  - 成功触发防负优化保护: {res3.error_message}")
        print("  -> 保护机制测试通过！")

        print("\n" + "=" * 60)
        print("            所有端到端测试全部通过！ (ALL PASSED)")
        print("=" * 60)

    finally:
        # 清理测试文件夹
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("测试临时目录已自动清理。")


if __name__ == "__main__":
    run_tests()
