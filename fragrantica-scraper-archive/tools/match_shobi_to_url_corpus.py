from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("match_shobi_to_url_corpus_v4.py")), run_name="__main__")
