import ast
import os
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"{e.msg} (Line {e.lineno}, Col {e.offset})"
    except Exception as e:
        return False, str(e)

files_to_check = [
    'scoring_engine.py',
    'normalizer.py',
    'draft_engine.py',
    'timeline_engine.py',
    'engine_core.py',
    'decision_support_engine.py',
    'defence_engine.py',
    'api.py'
]

results = []
for f in files_to_check:
    if os.path.exists(f):
        success, err = check_syntax(f)
        results.append((f, success, err))
    else:
        results.append((f, False, "File not found"))

for f, success, err in results:
    status = "OK" if success else f"ERROR: {err}"
    print(f"{f}: {status}")
