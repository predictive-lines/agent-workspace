#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List


def parse_group_sizes(raw: str, image_count: int) -> List[int]:
    sizes = [int(part.strip()) for part in raw.split(',') if part.strip()]
    if not sizes:
        raise ValueError('group sizes cannot be empty')
    if any(size <= 0 for size in sizes):
        raise ValueError('group sizes must all be positive integers')
    if sum(sizes) != image_count:
        raise ValueError(f'group sizes sum to {sum(sizes)} but image count is {image_count}')
    return sizes


def build_bottles(images: List[str], group_sizes: List[int]):
    bottles = []
    cursor = 0
    for idx, size in enumerate(group_sizes, start=1):
        group = images[cursor:cursor + size]
        cursor += size
        bottles.append({
            'bottle_id': f'bottle-{idx:03d}',
            'image_paths': group,
            'producer': None,
            'wine_name': None,
            'vintage': None,
            'varietal': None,
            'region': None,
            'country': None,
            'confidence': None,
            'notes': [],
            'status': 'pending_extraction',
        })
    return bottles


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a structured wine-photo ingest manifest.')
    parser.add_argument('images', nargs='+', help='Image paths in batch order')
    parser.add_argument('--source', default='local', help='Source system, e.g. slack')
    parser.add_argument('--group-sizes', required=True, help='Comma-separated bottle image counts, e.g. 3,1,1')
    parser.add_argument('--output', help='Write JSON to this path instead of stdout')
    parser.add_argument('--batch-id', help='Optional stable batch id')
    args = parser.parse_args()

    image_paths = [str(Path(p).resolve()) for p in args.images]
    missing = [p for p in image_paths if not os.path.exists(p)]
    if missing:
        print(json.dumps({'error': 'missing_files', 'paths': missing}, indent=2), file=sys.stderr)
        return 1

    try:
        group_sizes = parse_group_sizes(args.group_sizes, len(image_paths))
    except ValueError as exc:
        print(json.dumps({'error': 'invalid_group_sizes', 'message': str(exc)}, indent=2), file=sys.stderr)
        return 1

    manifest = {
        'batch_id': args.batch_id or f"wine-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        'created_at': datetime.now().astimezone().isoformat(),
        'source': args.source,
        'image_count': len(image_paths),
        'bottle_count': len(group_sizes),
        'bottles': build_bottles(image_paths, group_sizes),
        'status': 'pending_extraction',
    }

    payload = json.dumps(manifest, indent=2)
    if args.output:
        Path(args.output).write_text(payload + '\n', encoding='utf-8')
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
