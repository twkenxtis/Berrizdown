import asyncio
import shutil

from lib.path import Path
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn
from static.color import Color
from unit.handle.handle_log import setup_logging

logger = setup_logging("merge", "blush")


class MERGE:
    MAX_CONCURRENCY = 4
    BUFFER_SIZE = 4 * 1024 * 1024

    @staticmethod
    async def binary_merge(
        output_file: Path,
        init_files: list[Path],
        segments: list[Path],
        track_type: str,
    ) -> bool:
        temp_dir: Path = output_file.parent / f"temp_merging_{track_type}"
        temp_dir.mkdir(exist_ok=True)

        try:
            # MPD init file
            if init_files:
                await asyncio.to_thread(shutil.copyfile, init_files[0], output_file)
                logger.debug(f"{track_type} init file copied")

            # 預先收集 size 避免後續重複 stat()
            seg_info: list[tuple[Path, int]] = [(p, p.stat().st_size) for p in segments]
            total_bytes = sum(size for _, size in seg_info)

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            )

            # 分塊
            chunk_size = 30
            chunks: list[list[tuple[Path, int]]] = [seg_info[i : i + chunk_size] for i in range(0, len(seg_info), chunk_size)]

            semaphore = asyncio.Semaphore(MERGE.MAX_CONCURRENCY)

            async def process_chunk(idx, chunk):
                try:
                    async with semaphore:
                        return await MERGE.process_chunk_python(chunk, temp_dir / f"chunk_{idx}.tmp", progress, task_id, idx)
                except asyncio.CancelledError:
                    return False

            with progress:
                task_id = progress.add_task(f"[cyan]{track_type}[/] merging", total=total_bytes)
                try:
                    results = await asyncio.gather(
                        *[process_chunk(idx, chunk) for idx, chunk in enumerate(chunks)],
                        return_exceptions=True,
                    )
                except asyncio.CancelledError:
                    return False

                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"{track_type} chunk {idx} failed: {result}")
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return False

            # 合併所有 chunk
            with open(output_file, "ab") as outfile:
                for idx in range(len(chunks)):
                    temp_file = temp_dir / f"chunk_{idx}.tmp"
                    if not temp_file.exists():
                        continue
                    try:
                        with open(temp_file, "rb") as infile:
                            shutil.copyfileobj(infile, outfile, length=MERGE.BUFFER_SIZE)
                    except KeyboardInterrupt:
                        return False

            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"{Color.fg('light_gray')}{track_type} {Color.fg('sienna')}Merger completed: {Color.fg('ash_gray')}{output_file}{Color.reset()}")
            return True

        except Exception as e:
            logger.error(f"{track_type} Merger failed: {str(e)}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

    @staticmethod
    async def process_chunk_python(
        segments: list[tuple[Path, int]],
        temp_file: Path,
        progress: Progress,
        task_id: int,
        chunk_idx: int,
    ) -> bool:
        try:

            def copy_segments():
                with open(temp_file, "wb") as outfile:
                    for seg, size in segments:
                        with open(seg, "rb") as infile:
                            shutil.copyfileobj(infile, outfile, length=MERGE.BUFFER_SIZE)
                        progress.update(task_id, advance=size)

            await asyncio.to_thread(copy_segments)
            return True

        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_idx}: {e}")
            return False
