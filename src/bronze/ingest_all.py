import sys
import os

REPO = "/Workspace/Repos/ankushkumar645@gmail.com/databricks-medallion-pipeline"
DATA = f"{REPO}/data"
SRC = f"{REPO}/src"
sys.path.insert(0, SRC)

os.environ["MEDALLION_CATALOG"] = "databricks_assignment"
os.environ["MEDALLION_SOURCE_BASE_PATH"] = DATA
os.environ["MEDALLION_BRONZE_WRITE_MODE"] = "overwrite"

from bronze.ingest_utils import configure_src_path, run_ingest_all, setup_logging

configure_src_path()
setup_logging()

code = run_ingest_all([
    "--catalog", "databricks_assignment",
    "--source-base-path", DATA,
    "--write-mode", "overwrite",
])
if code != 0:
    raise RuntimeError("Bronze ingest failed")
print("Bronze OK")