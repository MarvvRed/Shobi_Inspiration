from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
runpy.run_path(str(here / "match_shobi_to_url_corpus_v7.py"), run_name="__main__")
runpy.run_path(str(here / "analyze_unresolved_mapping.py"), run_name="__main__")
