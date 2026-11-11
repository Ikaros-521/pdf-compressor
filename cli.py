"""PDF 压缩命令行工具 (CLI)
支持单文件、多文件通配符匹配、目录递归批量压缩。
"""

import argparse
import glob
import os
import sys
import time
from pathlib import Path
from typing import List

from compressor import MODE_PRESETS, PDFCompressor, format_size


# 终端 ANSI 样式输出
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def print_banner():
    banner = f"""{Style.CYAN}{Style.BOLD}
======================================================
           PDF 智能高效压缩工具 (CLI 版)
======================================================{Style.RESET}"""
    print(banner)


def collect_pdf_files(paths: List[str], recursive: bool = False) -> List[Path]:
    """收集待处理的 PDF 文件列表"""
    files = []
    for p_str in paths:
        # 支持 Windows 通配符
        matched = glob.glob(p_str, recursive=recursive)
        if not matched:
            target = Path(p_str)
            if target.is_file() and target.suffix.lower() == ".pdf":
                files.append(target.resolve())
            elif target.is_dir():
                pattern = "**/*.pdf" if recursive else "*.pdf"
                files.extend([f.resolve() for f in target.glob(pattern)])
        else:
            for item in matched:
                target = Path(item)
                if target.is_file() and target.suffix.lower() == ".pdf":
                    files.append(target.resolve())
                elif target.is_dir():
                    pattern = "**/*.pdf" if recursive else "*.pdf"
                    files.extend([f.resolve() for f in target.glob(pattern)])

    # 去重并排序
    unique_files = sorted(list({f for f in files}))
    return unique_files


def main():
    # 启用 Windows 控制台 ANSI 颜色
    if sys.platform == "win32":
        os.system("")

    parser = argparse.ArgumentParser(
        description="PDF 智能高效压缩工具 - 基于底层流优化与自适应图像降采样",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
常用示例:
  # 1. 默认平衡模式压缩单个文件（输出为 原文件名_compressed.pdf）:
  python cli.py report.pdf

  # 2. 指定输出路径:
  python cli.py report.pdf -o output/report_mini.pdf

  # 3. 批量压缩整个目录下的所有 PDF 到目标目录:
  python cli.py ./documents/ -o ./compressed_docs/

  # 4. 递归压缩目录（包括子文件夹）:
  python cli.py ./documents/ -o ./compressed_docs/ -r

  # 5. 采用极限压缩模式（追求极小体积）:
  python cli.py report.pdf -m aggressive

  # 6. 自定义图像质量和 DPI:
  python cli.py report.pdf -q 60 --dpi 120

  # 7. 原地覆盖压缩（谨慎使用）:
  python cli.py report.pdf --replace
        """,
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="输入文件或目录路径（支持多个路径及通配符，如 *.pdf 或 ./docs/）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出文件路径或输出目录（批量压缩时必须为目录）",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["balanced", "light", "aggressive", "lossless", "custom"],
        default="balanced",
        help="压缩模式预设 (默认: balanced)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=None,
        help="图像重压缩质量 1-100 (留空则使用对应模式预设)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="目标图像 DPI (如 150, 100, 72，留空则使用对应模式预设)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="遍历目录时递归查找所有子目录下的 PDF",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="原地覆盖原文件（若压缩后体积未减少则不会覆盖）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使压缩后体积反而变大，也强制保存新文件",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=None,
        help="加密 PDF 文件的密码",
    )

    args = parser.parse_args()

    print_banner()

    # 收集文件
    files = collect_pdf_files(args.inputs, recursive=args.recursive)
    if not files:
        print(f"{Style.RED}未找到任何匹配的 PDF 文件！{Style.RESET}")
        print(f"请检查输入路径: {args.inputs}")
        sys.exit(1)

    # 检查输出设置
    output_path = Path(args.output).resolve() if args.output else None
    if len(files) > 1 and output_path and not args.replace:
        if output_path.suffix.lower() == ".pdf":
            print(
                f"{Style.RED}错误: 批量压缩多个文件时，--output 必须为目录而不是单个文件名！{Style.RESET}"
            )
            sys.exit(1)
        output_path.mkdir(parents=True, exist_ok=True)

    # 显示任务参数
    mode_desc = MODE_PRESETS.get(args.mode, {}).get("description", "自定义模式")
    print(f"{Style.BOLD}当前配置:{Style.RESET}")
    print(f"  模式      : {Style.CYAN}{args.mode}{Style.RESET} ({mode_desc})")
    if args.quality is not None:
        print(f"  质量      : {args.quality}")
    if args.dpi is not None:
        print(f"  DPI 目标  : {args.dpi}")
    print(f"  待处理文件: {len(files)} 个")
    print("-" * 54)

    # 初始化压缩器
    compressor = PDFCompressor(
        mode=args.mode,
        quality=args.quality,
        dpi_target=args.dpi,
        skip_if_larger=not args.force,
    )

    start_total_time = time.time()
    results = []
    total_orig_size = 0
    total_comp_size = 0

    # 循环处理文件
    for idx, f in enumerate(files, start=1):
        # 确定目标输出路径
        if args.replace:
            dest = f
        elif output_path:
            if output_path.suffix.lower() == ".pdf":
                dest = output_path
            else:
                dest = output_path / f.name
        else:
            dest = None  # 默认生成 原文件名_compressed.pdf

        print(f"[{idx}/{len(files)}] 正在压缩: {Style.BOLD}{f.name}{Style.RESET} ...", end=" ", flush=True)

        res = compressor.compress_file(f, dest, password=args.password)
        results.append(res)

        total_orig_size += res.original_size

        if res.status == "SUCCESS":
            total_comp_size += res.compressed_size
            print(
                f"{Style.GREEN}成功!{Style.RESET} "
                f"({format_size(res.original_size)} -> {format_size(res.compressed_size)}, "
                f"{Style.BOLD}减少 {res.ratio}%{Style.RESET}, 耗时 {res.elapsed_time:.2f}s)"
            )
            print(f"       -> 输出: {res.output_path}")
        elif res.status == "SKIPPED_LARGER":
            total_comp_size += res.original_size
            print(
                f"{Style.YELLOW}跳过{Style.RESET} "
                f"({format_size(res.original_size)}, {res.error_message})"
            )
        else:
            print(f"{Style.RED}失败!{Style.RESET} (原因: {res.error_message})")

    total_time = time.time() - start_total_time

    # 打印总结
    success_count = sum(1 for r in results if r.status == "SUCCESS")
    skipped_count = sum(1 for r in results if r.status == "SKIPPED_LARGER")
    failed_count = sum(1 for r in results if r.status == "ERROR")

    overall_ratio = (
        ((total_orig_size - total_comp_size) / total_orig_size) * 100.0
        if total_orig_size > 0
        else 0.0
    )
    saved_bytes = total_orig_size - total_comp_size

    print("\n" + "=" * 54)
    print(f"{Style.BOLD}压缩统计报告:{Style.RESET}")
    print(f"  处理总数   : {len(files)} 个文件")
    print(
        f"  状态分布   : {Style.GREEN}成功 {success_count}{Style.RESET} | "
        f"{Style.YELLOW}已最优跳过 {skipped_count}{Style.RESET} | "
        f"{Style.RED}失败 {failed_count}{Style.RESET}"
    )
    print(f"  原始总大小 : {format_size(total_orig_size)}")
    print(f"  压缩后总计 : {format_size(total_comp_size)}")
    if saved_bytes > 0:
        print(
            f"  {Style.BOLD}总体节省   : {format_size(saved_bytes)} ({overall_ratio:.2f}% 体积缩减){Style.RESET}"
        )
    print(f"  总耗时     : {total_time:.2f} 秒")
    print("=" * 54)


if __name__ == "__main__":
    main()
