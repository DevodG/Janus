"""memory.py — single-writer memory for Janus V2 (Finalised Architecture §3).

One owner for all persistence:
  - pinned blocks: USER.md / STATE.md (Letta paging *pattern*, no runtime)
  - append-only JSONL: cases.jsonl / corrections.jsonl
  - SQLite facts table with temporal validity (valid_from/valid_to/provenance)
Tools: memory_search / memory_append / memory_replace, each diff-logged + revertible.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

DATA = Path(__file__).parent / "data"


class Memory:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else DATA
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "facts.db", check_same_thread=False)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS facts(
            id TEXT PRIMARY KEY, subject TEXT, predicate TEXT, object TEXT,
            valid_from REAL, valid_to REAL, episode_id TEXT, source TEXT,
            confidence REAL)"""
        )
        self.db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(subject, predicate, object)")
        self.db.commit()
        self._diff_log = self.root / "memory_diffs.jsonl"

    # -- pinned blocks -----------------------------------------------------
    def _block(self, name: str) -> str:
        p = self.root / name
        return p.read_text() if p.exists() else ""

    def pinned(self) -> dict:
        return {"user": self._block("USER.md"), "state": self._block("STATE.md")}

    # -- facts (temporal) --------------------------------------------------
    def _quarantine(self, kind: str, payload: dict, reason: str) -> None:
        """Quality gate (Sangrah ETL pattern): rejected writes are logged, never stored."""
        self._append("quarantine.jsonl", {"ts": time.time(), "kind": kind,
                                          "reason": reason, "payload": payload})

    def _gate(self, kind: str, fields: dict) -> bool:
        for k, v in fields.items():
            if v is None or (isinstance(v, str) and not v.strip()):
                self._quarantine(kind, fields, f"empty field: {k}")
                return False
            if isinstance(v, str) and len(v) > 2000:
                self._quarantine(kind, fields, f"oversized field: {k}")
                return False
        return True

    def add_fact(self, subject, predicate, obj, source="user", confidence=1.0,
                 episode_id=None, valid_from=None):
        if not self._gate("fact", {"subject": subject, "predicate": predicate, "object": obj}):
            return ""
        fid = uuid.uuid4().hex[:12]
        now = valid_from if valid_from is not None else time.time()
        # invalidate superseded fact: same subject+predicate still open
        self.db.execute(
            "UPDATE facts SET valid_to=? WHERE subject=? AND predicate=? AND valid_to IS NULL",
            (now, subject, predicate))
        self.db.execute(
            "INSERT INTO facts VALUES(?,?,?,?,?,NULL,?,?,?)",
            (fid, subject, predicate, str(obj), now, episode_id or "", source, confidence))
        self.db.execute("INSERT INTO facts_fts(rowid, subject, predicate, object) "
                        "VALUES((SELECT MAX(rowid) FROM facts),?,?,?)",
                        (subject, predicate, str(obj)))
        self.db.commit()
        return fid

    # -- retrieval: FTS5 keyword + overlap fallback, fused ------------------
    def retrieve(self, query: str, top: int = 8) -> list[dict]:
        """Hybrid retrieval: FTS5 BM25 first, word-overlap rerank. Provenance kept."""
        fused: dict[str, float] = {}
        rows: dict[str, dict] = {}
        try:
            for subj, pred, obj, rank in self.db.execute(
                    "SELECT f.subject, f.predicate, f.object, facts_fts.rank FROM facts_fts "
                    "JOIN facts f ON f.rowid = facts_fts.rowid "
                    "WHERE facts_fts MATCH ? AND f.valid_to IS NULL ORDER BY facts_fts.rank LIMIT ?",
                    (query, top)):
                key = subj + pred + obj
                fused[key] = fused.get(key, 0.0) + (1.0 / (1.0 + abs(rank)))
                rows[key] = {"subject": subj, "predicate": pred, "object": obj}
        except Exception:
            pass
        for f in self.facts_now():
            s = self._overlap(query, f"{f['subject']} {f['predicate']} {f['object']}")
            if s > 0:
                key = f["subject"] + f["predicate"] + f["object"]
                fused[key] = fused.get(key, 0.0) + 0.3 * s
                rows[key] = f
        ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:top]
        return [rows[k] for k, _ in ranked]

    def facts_now(self, subject: str | None = None) -> list[dict]:
        q = "SELECT subject,predicate,object,source,confidence FROM facts WHERE valid_to IS NULL"
        args: tuple = ()
        if subject:
            q += " AND subject=?"
            args = (subject,)
        return [dict(zip(("subject", "predicate", "object", "source", "confidence"), r))
                for r in self.db.execute(q, args)]

    def facts_at(self, ts: float) -> list[dict]:
        rows = self.db.execute(
            "SELECT subject,predicate,object FROM facts "
            "WHERE valid_from<=? AND (valid_to IS NULL OR valid_to>?)", (ts, ts))
        return [dict(zip(("subject", "predicate", "object"), r)) for r in rows]

    # -- append-only JSONL ---------------------------------------------------
    def _append(self, name: str, row: dict) -> None:
        with open(self.root / name, "a") as f:
            f.write(json.dumps(row) + "\n")

    def _read(self, name: str) -> list[dict]:
        p = self.root / name
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

    def log_case(self, case: dict) -> None:
        self._append("cases.jsonl", case)

    def add_correction(self, question: str, wrong: str, correct: str) -> None:
        """Verbatim user correction — retrieved before any general instruction."""
        if not self._gate("correction", {"question": question, "correct": correct}):
            return
        if any(r["question"] == question and r["correct"] == correct
               for r in self._read("corrections.jsonl")):
            self._quarantine("correction", {"question": question}, "duplicate correction")
            return
        self._append("corrections.jsonl",
                     {"ts": time.time(), "question": question, "wrong": wrong, "correct": correct})

    @staticmethod
    def _overlap(a: str, b: str) -> int:
        sa = {w.strip("?.$,").lower() for w in a.split() if len(w) > 2}
        sb = {w.strip("?.$,").lower() for w in b.split() if len(w) > 2}
        return len(sa & sb)

    def corrections_for(self, question: str, top: int = 3) -> list[dict]:
        rows = self._read("corrections.jsonl")
        scored = sorted(((self._overlap(question, r["question"]), r) for r in rows),
                        key=lambda t: -t[0])
        return [r for s, r in scored if s > 0][:top]

    def episodic_for(self, question: str, top: int = 3) -> list[dict]:
        rows = self._read("cases.jsonl")
        scored = sorted(((self._overlap(question, r.get("question", "")), r) for r in rows),
                        key=lambda t: -t[0])
        return [r for s, r in scored if s > 0][:top]

    # -- skill library (Voyager pattern: gated, success-rated, composable) ---
    def add_skill(self, name: str, trigger: str, steps: list[str]) -> None:
        rows = [r for r in self._read("skills.jsonl") if r["name"] != name]
        rows.append({"name": name, "trigger": trigger, "steps": steps,
                     "attempts": 0, "successes": 0})
        (self.root / "skills.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n")

    def skills_for(self, question: str, top: int = 2) -> list[dict]:
        rows = self._read("skills.jsonl")
        scored = sorted(((self._overlap(question, r["trigger"]), r) for r in rows),
                        key=lambda t: -t[0])
        return [r for s, r in scored if s > 0][:top]

    def record_skill_outcome(self, name: str, ok: bool) -> None:
        rows = self._read("skills.jsonl")
        for r in rows:
            if r["name"] == name:
                r["attempts"] += 1
                r["successes"] += int(ok)
        (self.root / "skills.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))

    def update_self_model(self, weaknesses: list[str], strengths: list[str] | None = None) -> str:
        """Janus rewrites its own self-model from measured gaps (diff-logged)."""
        p = self.root / "SELF.md"
        old = p.read_text() if p.exists() else ""
        lines = ["# Janus self-model", "Name: Janus. Role: general assistant, self-learning.",
                 "Strengths: " + ("; ".join(strengths) if strengths else "verified computation, corrections")]
        lines.append("Known weaknesses (measured, auto-updated):")
        lines += [f"- {w}" for w in (weaknesses or ["none measured"])]
        lines.append("Goals: answer correctly, cite or compute, correct fast, extend own skills via the gate.")
        p.write_text("\n".join(lines) + "\n")
        return self._log_diff("self-model", {"weaknesses": weaknesses},
                              {"block": "SELF.md", "restore": old})

    def self_model(self) -> str:
        """SELF.md: readable self-model (capabilities, weaknesses, goals)."""
        p = self.root / "SELF.md"
        if p.exists():
            return p.read_text()
        return ("# Janus self-model\nName: Janus. Role: general assistant, finance-strong.\n"
                "Known weaknesses: no verified answer without a source or computation; "
                "voice/dissonance uncalibrated.\nGoals: answer correctly, cite, correct fast.\n")

    # -- tool surface (diff-logged, revertible) ------------------------------
    def _log_diff(self, op: str, detail: dict, inverse: dict) -> str:
        did = uuid.uuid4().hex[:12]
        self._append("memory_diffs.jsonl",
                     {"id": did, "ts": time.time(), "op": op, "detail": detail, "inverse": inverse})
        return did

    def memory_search(self, query: str) -> list[dict]:
        hits = self.facts_now()
        q = query.lower()
        return [h for h in hits if q in h["subject"].lower() or q in h["object"].lower()]

    def memory_append(self, block: str, text: str) -> str:
        assert block in ("USER.md", "STATE.md"), f"unknown block {block}"
        p = self.root / block
        old = p.read_text() if p.exists() else ""
        p.write_text(old + text + "\n")
        return self._log_diff("append", {"block": block, "text": text},
                              {"block": block, "restore": old})

    def memory_replace(self, block: str, old_text: str, new_text: str) -> str:
        assert block in ("USER.md", "STATE.md"), f"unknown block {block}"
        p = self.root / block
        cur = p.read_text() if p.exists() else ""
        assert old_text in cur, "old_text not present"
        p.write_text(cur.replace(old_text, new_text, 1))
        return self._log_diff("replace", {"block": block, "old": old_text, "new": new_text},
                              {"block": block, "restore": cur})

    def revert(self, diff_id: str) -> bool:
        for row in self._read("memory_diffs.jsonl"):
            if row["id"] == diff_id:
                inv = row["inverse"]
                (self.root / inv["block"]).write_text(inv["restore"])
                return True
        return False
