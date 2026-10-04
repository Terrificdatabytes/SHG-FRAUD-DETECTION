from pathlib import Path
def test_answer_key_not_in_runtime():
 root=Path(__file__).parents[1]
 for p in [root/'app.py',*list((root/'core').glob('*.py'))]: assert 'manifest.json' not in p.read_text()
