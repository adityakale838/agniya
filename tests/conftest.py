import os
import tempfile

# The API server persists /api/v2 columns; keep test runs out of the real store.
os.environ.setdefault("AGNIYA_STORE", os.path.join(tempfile.mkdtemp(prefix="agniya-test-"), "store.sqlite3"))
