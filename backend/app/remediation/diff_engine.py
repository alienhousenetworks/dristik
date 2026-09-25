"""
Dristik AI Structured Diff Engine
Computes unified character and line-level diffs for RemediationPatch inspection.
Produces formatted visual snippets for dashboard presentation and Pull Request bodies.
"""
import difflib
from typing import Dict, Any, List
from app.domain.models import RemediationPatch

class DiffEngine:
    """
    Computes human-readable and machine-executable diffs.
    """

    def generate_unified_diff(self, patch: RemediationPatch) -> str:
        before_lines = (patch.before_snippet or "").splitlines(keepends=True)
        after_lines = (patch.after_snippet or "").splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{patch.target_file}",
            tofile=f"b/{patch.target_file}",
            lineterm=""
        )
        return "\n".join(diff)

    def generate_diff_summary(self, patch: RemediationPatch) -> Dict[str, Any]:
        before_lines = (patch.before_snippet or "").splitlines()
        after_lines = (patch.after_snippet or "").splitlines()

        matcher = difflib.SequenceMatcher(None, before_lines, after_lines)
        added_count = 0
        removed_count = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                removed_count += (i2 - i1)
                added_count += (j2 - j1)
            elif tag == 'delete':
                removed_count += (i2 - i1)
            elif tag == 'insert':
                added_count += (j2 - j1)

        return {
            "patch_id": patch.patch_id,
            "title": patch.title,
            "target_file": patch.target_file,
            "lines_added": added_count,
            "lines_removed": removed_count,
            "unified_diff": self.generate_unified_diff(patch),
            "before_snippet": patch.before_snippet,
            "after_snippet": patch.after_snippet,
            "risk_level": patch.risk_level.value,
        }

diff_engine = DiffEngine()
