"""PDF 自动化监听监控服务 (Watcher)
无人值守后台监控指定文件夹，自动将新放入的 PDF 文件压缩并输出到目标文件夹。
"""

import argparse
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from compressor import MODE_PRESETS, PDFCompressor, format_size


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def log(msg: str, level: str = "INFO"):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"{Style.GRAY}[{now_str}]{Style.RESET}"
    if level == "SUCCESS":
        print(f"{prefix} {Style.GREEN}[成功]{Style.RESET} {msg}")
    elif level == "WARN":
        print(f"{prefix} {Style.YELLOW}[警告]{Style.RESET} {msg}")
    elif level == "ERROR":
        print(f"{prefix} {Style.RED}[错误]{Style.RESET} {msg}")
    else:
        print(f"{prefix} {Style.CYAN}[信息]{Style.RESET} {msg}")


def wait_for_file_ready(file_path: Path, timeout: float = 10.0, check_interval: float = 0.5) -> bool:
    """等待文件完全写入完成（防止文件仍在复制或下载过程中时被提前处理）"""
    start_time = time.time()
    last_size = -1

    while time.time() - start_time < timeout:
        try:
            if not file_path.exists():
                return False
            current_size = file_path.stat().st_size
            if current_size == last_size and current_size > 0:
                # 尝试以二进制只读模式打开，确认无文件锁
                with open(file_path, "rb") as f:
                    f.read(1024)
                return True
            last_size = current_size
        except (IOError, OSError, PermissionError):
            pass

        time.sleep(check_interval)

    return False


def run_watcher(
    watch_dir: Path,
    output_dir: Path,
    archive_dir: Path,
    compressor: PDFCompressor,
    poll_interval: float = 2.0,
):
    # 确保目录存在
    watch_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    log(f"启动 PDF 自动化监控服务...", "INFO")
    log(f"  监控输入目录 : {watch_dir}", "INFO")
    log(f"  压缩输出目录 : {output_dir}", "INFO")
    log(f"  原件归档目录 : {archive_dir}", "INFO")
    log(f"  轮询检查周期 : {poll_interval} 秒", "INFO")
    log("提示: 只需将任意 PDF 文件放入监控输入目录，即可自动触发压缩！(按 Ctrl+C 停止)")
    print("-" * 60)

    try:
        while True:
            # 扫描所有 .pdf 文件
            pdf_files = [f for f in watch_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]

            for pdf_path in pdf_files:
                log(f"检测到新文件: {pdf_path.name}，正在校验文件完整性...")

                if not wait_for_file_ready(pdf_path):
                    log(f"文件未就绪或被占用，跳过等待下次处理: {pdf_path.name}", "WARN")
                    continue

                dest_path = output_dir / pdf_path.name
                log(f"开始压缩: {pdf_path.name} ...")

                res = compressor.compress_file(pdf_path, dest_path)

                if res.status == "SUCCESS":
                    log(
                        f"压缩完成: {pdf_path.name} ({format_size(res.original_size)} -> {format_size(res.compressed_size)}, "
                        f"减少 {res.ratio}%, 耗时 {res.elapsed_time:.2f}s)",
                        "SUCCESS",
                    )
                elif res.status == "SKIPPED_LARGER":
                    log(f"文件已最优，已保留原体积: {pdf_path.name}", "WARN")
                else:
                    log(f"压缩失败: {pdf_path.name} - {res.error_message}", "ERROR")

                # 归档原始文件
                try:
                    archive_dest = archive_dir / pdf_path.name
                    # 若归档已存在同名文件，添加时间戳
                    if archive_dest.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        archive_dest = archive_dir / f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"
                    shutil.move(str(pdf_path), str(archive_dest))
                    log(f"原件已安全归档至: {archive_dest.name}")
                except Exception as e:
                    log(f"归档原件失败: {e}", "ERROR")

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        log("监控服务已安全退出。")


def main():
    if sys.platform == "win32":
        os.system("")

    parser = argparse.ArgumentParser(
        description="PDF 自动化文件夹监控压缩服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-w",
        "--watch-dir",
        default="./watch_input",
        help="监控的输入文件夹 (默认: ./watch_input)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./watch_output",
        help="压缩后的输出文件夹 (默认: ./watch_output)",
    )
    parser.add_argument(
        "-a",
        "--archive-dir",
        default="./watch_archive",
        help="处理完毕后原件的归档文件夹 (默认: ./watch_archive)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["balanced", "light", "aggressive", "lossless"],
        default="balanced",
        help="压缩模式 (默认: balanced)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=None,
        help="图像质量 1-100",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="目标图像 DPI",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="扫描轮询时间间隔（秒，默认 2.0）",
    )

    args = parser.parse_args()

    watch_path = Path(args.watch_dir).resolve()
    output_path = Path(args.output_dir).resolve()
    archive_path = Path(args.archive_dir).resolve()

    compressor = PDFCompressor(
        mode=args.mode,
        quality=args.quality,
        dpi_target=args.dpi,
    )

    run_watcher(
        watch_dir=watch_path,
        output_dir=output_path,
        archive_dir=archive_path,
        compressor=compressor,
        poll_interval=args.interval,
    )


if __name__ == "__main__":
    main()
