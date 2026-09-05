from pathlib import Path
import runpy

# Curated web batches 3, 4, 5, 6 and 7 applied 2026-09-05.
here = Path(__file__).resolve().parent
runpy.run_path(str(here / "match_shobi_to_url_corpus_v7.py"), run_name="__main__")
runpy.run_path(str(here / "merge_web_confirmed.py"), run_name="__main__")
runpy.run_path(str(here / "analyze_unresolved_mapping.py"), run_name="__main__")
runpy.run_path(str(here / "prepare_web_resolution_batches.py"), run_name="__main__")
