#!/usr/bin/env python3
"""Static guard: managed UI contracts and frontend must not expose company selectors."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGED = ROOT / 'managed'

violations = []
for path in MANAGED.rglob('*'):
    if not path.is_file() or path.suffix not in {'.py', '.ts', '.tsx', '.xml'}:
        continue
    if path.as_posix().endswith('managed/core/controllers/ui_api.py'):
        continue
    source = path.read_text(errors='ignore')
    if path.suffix in {'.ts', '.tsx'} and 'company_id' in source:
        violations.append(f'{path.relative_to(ROOT)} exposes company_id in frontend')
    if path.suffix == '.xml' and '<field name="company_id"' in source and 'managed/settings/views/actions.xml' not in path.as_posix():
        violations.append(f'{path.relative_to(ROOT)} exposes company_id in view')
    if path.suffix != '.py':
        continue
    try:
        tree = ast.parse(source)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != '_managed_ui_contract':
            continue
        segment = ast.get_source_segment(source, node) or ''
        if "'company_id'" in segment or '"company_id"' in segment:
            violations.append(f'{path.relative_to(ROOT)} exposes company_id in managed contract')

assert not violations, '\n'.join(violations)
print('managed company selector self-check passed')
