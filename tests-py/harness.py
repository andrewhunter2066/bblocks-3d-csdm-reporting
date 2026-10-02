"""Run this register's `python` transforms locally, the way the OGC Building Blocks postprocessor does.

Each transform's code (`ref:` file) is exec'd with `input_data`, `transform_metadata` and a
`get_transformer()` that resolves other transforms in this register. Standard library only, so the
logic can be tested without Docker; schema validation of outputs stays with the postprocessor
(`outputs.profiles`), which is the authoritative check.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES = REPO_ROOT / '_sources'
IDENTIFIER_PREFIX = 'csdm.reporting.'


def _bblock_dir(bblock_id: str) -> Path:
    if not bblock_id.startswith(IDENTIFIER_PREFIX):
        raise KeyError(f'{bblock_id} is not a building block of this register')
    return SOURCES.joinpath(*bblock_id[len(IDENTIFIER_PREFIX):].split('.'))


def _transform_refs(bblock_dir: Path) -> dict[str, Path]:
    """Map transform id -> code file, read from transforms.yaml (`- id:` ... `ref:` pairs)."""
    text = (bblock_dir / 'transforms.yaml').read_text(encoding='utf-8')
    refs = {}
    for block in re.split(r'^\s*- id:\s*', text, flags=re.M)[1:]:
        transform_id = block.split()[0]
        match = re.search(r'^\s*ref:\s*(\S+)', block, flags=re.M)
        if match:
            refs[transform_id] = bblock_dir / match.group(1)
    return refs


def run_transform(bblock_id: str, transform_id: str, input_data: str, _stack: tuple = (),
                  extra_metadata: dict | None = None) -> str:
    key = (bblock_id, transform_id)
    if key in _stack:
        raise RuntimeError(f'Cycle detected: {key}')
    code_file = _transform_refs(_bblock_dir(bblock_id))[transform_id]

    def get_transformer(target_bblock: str, target_transform: str):
        def call(content, source_mime_type=None, extra_metadata=None):
            return run_transform(target_bblock, target_transform, content, _stack + (key,), extra_metadata)
        return call

    namespace = {
        'input_data': input_data,
        'output_data': None,
        'get_transformer': get_transformer,
        'transform_metadata': SimpleNamespace(
            metadata={**(extra_metadata or {}), '_nested_transform': bool(_stack)},
            context=SimpleNamespace(bblock_id=bblock_id),
            source_mime_type=None, target_mime_type=None),
    }
    exec(compile(code_file.read_text(encoding='utf-8'), str(code_file), 'exec'), namespace)
    return namespace['output_data']


def plain(obj):
    """Replace every ReportValue ({'value': ..., 'status': ...}) in a report by its bare value."""
    if isinstance(obj, dict):
        if 'status' in obj and 'value' in obj:
            return obj['value']
        return {key: plain(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [plain(item) for item in obj]
    return obj


def table_rows(html: str, table_id: str = 'lots') -> list[tuple[str, ...]]:
    """Text of each row of one table in a rendered report, with status markers and tags removed."""
    table = re.search(rf'<table id="{table_id}">(.*?)</table>', html, flags=re.S).group(1)
    rows = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', table, flags=re.S):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, flags=re.S)
        rows.append(tuple(re.sub(r'<[^>]+>', '', re.sub(r'<sup.*?</sup>', '', c, flags=re.S)).strip()
                          for c in cells))
    return rows
