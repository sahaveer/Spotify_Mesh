import os
import re
import urllib.parse
from typing import Generator, Optional
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

CHUNK_SIZE = 512 * 1024  # 512KB chunks for smooth buffering of audio and 1080p/4K video

def parse_range_header(range_header: str, file_size: int):
    """
    Parses 'Range: bytes=start-end' header and returns (start, end, content_length).
    """
    match = re.search(r"bytes=(\d+)-(\d*)", range_header)
    if not match:
        return 0, file_size - 1, file_size
    
    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(
            status_code=416,
            detail="Requested Range Not Satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    content_length = end - start + 1
    return start, end, content_length

def file_chunk_generator(file_path: str, start: int, end: int, chunk_size: int = CHUNK_SIZE) -> Generator[bytes, None, None]:
    """Reads a slice of an audio or video file in chunks without loading everything into memory."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data

def stream_audio(file_path: str, request: Request, mime_type: str = "audio/mpeg", download_filename: Optional[str] = None) -> StreamingResponse:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    is_download = request.query_params.get("download") == "true" or download_filename is not None

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": mime_type,
    }

    if is_download:
        safe_name = download_filename or os.path.basename(file_path)
        encoded_name = urllib.parse.quote(safe_name)
        headers["Content-Disposition"] = f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{encoded_name}'

    if range_header:
        start, end, content_length = parse_range_header(range_header, file_size)
        headers.update({
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
        })
        return StreamingResponse(
            file_chunk_generator(file_path, start, end),
            status_code=206,
            headers=headers
        )
    else:
        headers["Content-Length"] = str(file_size)
        return StreamingResponse(
            file_chunk_generator(file_path, 0, file_size - 1),
            status_code=200,
            headers=headers
        )
