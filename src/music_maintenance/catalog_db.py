"""SQLite persistence for the read-only catalog prototype."""
from __future__ import annotations
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
 id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
 extension TEXT NOT NULL, size INTEGER, modified_ns INTEGER, scan_time TEXT NOT NULL,
 available INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'DB', issue TEXT, artist TEXT, album_artist TEXT,
 album TEXT, title TEXT, track TEXT, year TEXT, genre TEXT, duration REAL,
 bitrate INTEGER, sample_rate INTEGER, artwork_state TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_album_artist ON files(album_artist);
CREATE TABLE IF NOT EXISTS lookup_results (
 id INTEGER PRIMARY KEY, file_path TEXT NOT NULL, provider TEXT NOT NULL,
 recording_id TEXT, release_id TEXT, score INTEGER, artist TEXT, title TEXT,
 release TEXT, date TEXT, evidence TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lookup_file ON lookup_results(file_path);
CREATE TABLE IF NOT EXISTS saved_plans (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending'
);
CREATE TABLE IF NOT EXISTS plan_items (
 id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES saved_plans(id), file_path TEXT NOT NULL,
 included INTEGER NOT NULL DEFAULT 1, planned_size INTEGER, planned_modified_ns INTEGER, proposal_json TEXT, artwork_json TEXT, status TEXT NOT NULL DEFAULT 'Plan - Pending', created_at TEXT NOT NULL
);
"""

class CatalogDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # The prototype scans in a worker thread while the UI reads the catalog.
        # Serialize access until the persistence layer is split into worker-owned
        # connections in the production implementation.
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        try:
            self.connection.execute("ALTER TABLE plan_items ADD COLUMN planned_size INTEGER")
            self.connection.execute("ALTER TABLE plan_items ADD COLUMN planned_modified_ns INTEGER")
        except sqlite3.OperationalError:
            pass
        for column in ("proposal_json TEXT", "artwork_json TEXT"):
            try:
                self.connection.execute(f"ALTER TABLE plan_items ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        try:
            self.connection.execute("ALTER TABLE plan_items ADD COLUMN status TEXT NOT NULL DEFAULT 'Plan - Pending'")
        except sqlite3.OperationalError:
            pass
        try:
            self.connection.execute("ALTER TABLE files ADD COLUMN status TEXT NOT NULL DEFAULT 'DB'")
        except sqlite3.OperationalError:
            pass
        self.connection.execute("UPDATE files SET status = 'Plan - Pending' WHERE status = 'Plain'")
        self.connection.commit()

    def upsert_file(self, values: dict[str, object]) -> None:
        columns = ", ".join(values)
        placeholders = ", ".join(f":{key}" for key in values)
        updates = ", ".join(f"{key}=excluded.{key}" for key in values if key != "path")
        with self._lock:
            self.connection.execute(f"INSERT INTO files ({columns}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {updates}", values)

    def rows(self, issues_only: bool = False, search: str = "", field: str = "All", case_sensitive: bool = False) -> list[sqlite3.Row]:
        clauses, params = [], []
        if issues_only: clauses.append("issue IS NOT NULL AND issue <> ''")
        if search:
            fields = {"Album artist": "album_artist", "Artist": "artist", "Album": "album", "Title": "title", "Filename": "filename"}
            columns = [fields[field]] if field in fields else ["album_artist", "artist", "album", "title", "filename", "path"]
            pattern = search if "*" in search else search
            operator = "GLOB" if case_sensitive else "LIKE"
            pattern = pattern if case_sensitive else pattern.replace("*", "%")
            if case_sensitive:
                pattern = pattern.replace("%", "*")
            clauses.append("(" + " OR ".join(f"{column} {operator} ?" for column in columns) + ")")
            params.extend([pattern] * len(columns))
        sql = "SELECT * FROM files" + ((" WHERE " + " AND ".join(clauses)) if clauses else "")
        sql += " ORDER BY album_artist, album, CAST(track AS INTEGER), title, filename"
        with self._lock:
            return list(self.connection.execute(sql, params))

    def row_for_path(self, path: str):
        with self._lock:
            return self.connection.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()

    def save_lookup_results(self, file_path: str, candidates: list[dict], created_at: str) -> None:
        with self._lock:
            # A new lookup supersedes the previous candidate set for this file.
            # Keeping old rows made repeated lookups appear as duplicate choices.
            self.connection.execute("DELETE FROM lookup_results WHERE file_path = ?", (file_path,))
            for candidate in candidates:
                import json
                self.connection.execute("INSERT INTO lookup_results (file_path, provider, recording_id, release_id, score, artist, title, release, date, evidence, created_at) VALUES (?, 'MusicBrainz', ?, ?, ?, ?, ?, ?, ?, ?, ?)", (file_path, candidate.get("recording_id"), candidate.get("release_id"), candidate.get("score"), candidate.get("artist"), candidate.get("title"), candidate.get("release"), candidate.get("date"), json.dumps(candidate), created_at))
            self.connection.commit()

    def clear_lookup_work(self, paths: list[str]) -> None:
        """Remove saved lookup candidates and return files to the DB status."""
        with self._lock:
            self.connection.executemany("DELETE FROM lookup_results WHERE file_path = ?", [(path,) for path in paths])
            self.connection.executemany("DELETE FROM plan_items WHERE file_path = ?", [(path,) for path in paths])
            self.connection.executemany("UPDATE files SET status = 'DB' WHERE path = ?", [(path,) for path in paths])
            self.connection.commit()

    def lookup_candidates(self, file_path: str):
        import json
        with self._lock:
            rows = self.connection.execute("SELECT evidence FROM lookup_results WHERE file_path = ? ORDER BY id", (file_path,)).fetchall()
        candidates = []
        seen = set()
        for row in rows:
            try:
                candidate = json.loads(row["evidence"])
                key = (candidate.get("recording_id"), candidate.get("release_id"), candidate.get("artist"), candidate.get("title"), candidate.get("date"))
                if key in seen: continue
                seen.add(key); candidates.append(candidate)
            except (TypeError, json.JSONDecodeError): pass
        return candidates

    def create_plan(self, name: str, paths: list[str], created_at: str, proposals: dict[str, dict] | None = None) -> int:
        import json
        with self._lock:
            cursor = self.connection.execute("INSERT INTO saved_plans (name, created_at) VALUES (?, ?)", (name, created_at))
            plan_id = int(cursor.lastrowid)
            items = []
            for path in paths:
                row = self.connection.execute("SELECT size, modified_ns FROM files WHERE path = ?", (path,)).fetchone()
                items.append((plan_id, path, row["size"] if row else None, row["modified_ns"] if row else None, json.dumps((proposals or {}).get(path, {})), created_at))
            self.connection.executemany("INSERT INTO plan_items (plan_id, file_path, planned_size, planned_modified_ns, proposal_json, created_at) VALUES (?, ?, ?, ?, ?, ?)", items)
            self.connection.commit()
            return plan_id

    def list_plans(self):
        with self._lock:
            return list(self.connection.execute("SELECT p.id, p.name, p.created_at, p.status, COUNT(i.id) AS item_count FROM saved_plans p LEFT JOIN plan_items i ON i.plan_id = p.id GROUP BY p.id ORDER BY p.created_at DESC"))

    def plan_status(self, plan_id: int) -> str:
        with self._lock:
            row = self.connection.execute("SELECT status FROM saved_plans WHERE id = ?", (plan_id,)).fetchone()
            return str(row["status"] if row else "")

    def set_plan_status(self, plan_id: int, status: str) -> None:
        with self._lock:
            self.connection.execute("UPDATE saved_plans SET status = ? WHERE id = ?", (status, plan_id)); self.connection.commit()

    def delete_plan(self, plan_id: int) -> None:
        with self._lock:
            self.connection.execute("DELETE FROM plan_items WHERE plan_id = ?", (plan_id,)); self.connection.execute("DELETE FROM saved_plans WHERE id = ?", (plan_id,)); self.connection.commit()

    def plan_items(self, plan_id: int):
        with self._lock:
            return list(self.connection.execute("SELECT i.file_path, i.planned_size, i.planned_modified_ns, i.proposal_json, i.artwork_json, i.status FROM plan_items i WHERE i.plan_id = ?", (plan_id,)))

    def set_plan_item_status(self, plan_id: int, file_path: str, status: str) -> None:
        with self._lock:
            self.connection.execute("UPDATE plan_items SET status = ? WHERE plan_id = ? AND file_path = ?", (status, plan_id, file_path)); self.connection.commit()

    def update_plan_proposal(self, plan_id: int, file_path: str, proposal: dict) -> None:
        import json
        with self._lock:
            plan = self.connection.execute("SELECT status FROM saved_plans WHERE id = ?", (plan_id,)).fetchone()
            if plan and plan["status"] != "Pending": return
            self.connection.execute("UPDATE plan_items SET proposal_json = ? WHERE plan_id = ? AND file_path = ?", (json.dumps(proposal), plan_id, file_path)); self.connection.commit()

    def add_plan_item(self, plan_id: int, file_path: str, proposal: dict, created_at: str) -> None:
        import json
        with self._lock:
            plan = self.connection.execute("SELECT status FROM saved_plans WHERE id = ?", (plan_id,)).fetchone()
            if plan and plan["status"] != "Pending": return
            existing = self.connection.execute("SELECT 1 FROM plan_items WHERE plan_id = ? AND file_path = ?", (plan_id, file_path)).fetchone()
            if existing: return
            row = self.connection.execute("SELECT size, modified_ns FROM files WHERE path = ?", (file_path,)).fetchone()
            self.connection.execute("INSERT INTO plan_items (plan_id, file_path, planned_size, planned_modified_ns, proposal_json, created_at) VALUES (?, ?, ?, ?, ?, ?)", (plan_id, file_path, row["size"] if row else None, row["modified_ns"] if row else None, json.dumps(proposal), created_at)); self.connection.commit()

    def set_status(self, paths: list[str], status: str) -> None:
        with self._lock:
            self.connection.executemany("UPDATE files SET status = ? WHERE path = ?", [(status, path) for path in paths]); self.connection.commit()

    def move_file_path(self, old_path: str, new_path: str) -> None:
        with self._lock:
            self.connection.execute("UPDATE files SET path = ?, filename = ? WHERE path = ?", (new_path, Path(new_path).name, old_path)); self.connection.commit()

    def signature_for_path(self, path: str):
        with self._lock:
            return self.connection.execute("SELECT size, modified_ns FROM files WHERE path = ?", (path,)).fetchone()

    def mark_missing_under(self, roots: list[Path], seen: set[str]) -> None:
        with self._lock:
            rows = self.connection.execute("SELECT path FROM files WHERE available = 1").fetchall()
            for row in rows:
                path = Path(row["path"])
                if any(path == root or root in path.parents for root in roots) and str(path) not in seen:
                    self.connection.execute("UPDATE files SET available = 0, issue = ? WHERE path = ?", ("File is missing", str(path)))

    def commit(self) -> None:
        with self._lock:
            self.connection.commit()

    def close(self) -> None:
        with self._lock:
            self.connection.close()
