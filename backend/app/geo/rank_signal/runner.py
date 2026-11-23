"""
Low-Cost, Credit-Native Rank Signal Trial Runner for Dristik.

Key optimizations over geo-aeo-tracker:
1. Code-built signals (S05, S06, S12, S13) cost $0 to rewrite.
2. Judge calls use max_tokens=16 (returns only {"choice":"A"|"B"}).
3. Generated A/B pairs are cached by (passage_hash, signal_id, keyword).
4. Per-tenant credit accounting (1 credit code-built, 2 credits LLM-built,
   10 credits full suite) with proportional refund on early stop/abort.
5. BYOK users pay 0 platform credits with a tight $0.50/run default safety brake.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.geo.rank_signal.features import (
    CATALOG_VERSION,
    Passage,
    SignalContext,
    SignalDef,
    check_pair,
    get_signal,
    is_eligible,
)
from app.geo.rank_signal.stats import CHECKPOINTS, MAX_TRIALS, posterior, verdict

CREDIT_COST_CODE_SIGNAL = 1
CREDIT_COST_LLM_SIGNAL = 2
CREDIT_COST_FULL_SUITE = 10
BYOK_DEFAULT_MAX_USD = float(os.environ.get("RANK_SIGNAL_MAX_USD_PER_RUN", "0.50") or 0.50)

JUDGE_SYSTEM = (
    "You are the retrieval step of an AI answer engine. You get a user query and two "
    'candidate passages, A and B. Pick the ONE passage you would rather use as a source '
    'to answer the query. You must pick one. Respond ONLY with JSON: {"choice":"A"} or {"choice":"B"}.'
)

REWRITE_SYSTEM = (
    "Make the smallest possible edit to the passage so it either adds or removes ONLY the requested "
    "feature, keeping all other facts and wording intact. Respond ONLY with JSON: "
    '{"with":"<passage with feature>","without":"<passage without feature>"}.'
)


class RankSignalTrial(BaseModel):
    passage_hash: str
    origin: str
    direction: str  # "add" | "remove"
    feature_side: str  # "A" | "B"
    outcome: str  # "win" | "loss" | "invalid"


class RankSignalExample(BaseModel):
    signal_id: str
    direction: str
    with_text: str
    without_text: str


class RankSignalCreditAccounting(BaseModel):
    billing_mode: str  # "credits" | "byok"
    reserved_credits: float = 0.0
    charged_credits: float = 0.0
    refunded_credits: float = 0.0
    estimated_llm_cost_usd: float = 0.0
    byok_cap_usd: Optional[float] = None


class RankSignalResult(BaseModel):
    run_id: str
    signal_id: str
    signal_name: str
    catalog_version: int = CATALOG_VERSION
    keyword: str
    target_url: str
    judge_model: str
    rewrite_model: str
    started_at: str
    finished_at: str
    n_valid: int
    wins: int
    win_rate_mean: Optional[float] = None
    ci_lo: Optional[float] = None
    ci_hi: Optional[float] = None
    verdict: str
    end_reason: str  # "verdict" | "max_trials" | "pool_exhausted" | "budget" | "aborted" | "error"
    rejected_pairs: int = 0
    skipped: int = 0
    cache_hits: int = 0
    credits: RankSignalCreditAccounting
    trials: List[RankSignalTrial] = Field(default_factory=list)
    examples: List[RankSignalExample] = Field(default_factory=list)


def credit_cost_for_signal(signal: SignalDef) -> int:
    return CREDIT_COST_CODE_SIGNAL if signal.build == "code" else CREDIT_COST_LLM_SIGNAL


def parse_judge_choice(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and parsed.get("choice") in ("A", "B"):
            return str(parsed["choice"])
    except Exception:
        pass
    m = re.match(r"^\W*(A|B)\b", text)
    return m.group(1) if m else None


# Type aliases for injectable judge/rewrite callables (enables 100% offline testing)
JudgeFn = Callable[[str, str, str, str], Awaitable[Tuple[Optional[str], float]]]
RewriteFn = Callable[[SignalDef, str, str, str], Awaitable[Tuple[Optional[Tuple[str, str, str]], float]]]


class RankSignalRunner:
    """Runs controlled paired A/B passage trials with pair caching and credit accounting."""

    def __init__(self) -> None:
        self._pair_cache: Dict[Tuple[str, str, str], Tuple[str, str, str]] = {}

    def clear_cache(self) -> None:
        self._pair_cache.clear()

    async def _default_judge(self, keyword: str, a: str, b: str, model: str) -> Tuple[Optional[str], float]:
        from app.core.inference.model_router import model_router

        user_msg = f"Query: {keyword}\n\n[Passage A]\n{a}\n\n[Passage B]\n{b}"
        resp = await model_router.generate_text(
            system_prompt=JUDGE_SYSTEM,
            user_prompt=user_msg,
            model_override=model or None,
            max_tokens=16,
            temperature=0.0,
        )
        choice = parse_judge_choice(resp.text if hasattr(resp, "text") else str(resp))
        cost = float(getattr(resp, "cost_usd", 0.0) or 0.0004)
        return choice, cost

    async def _default_rewrite(
        self, signal: SignalDef, passage_text: str, keyword: str, model: str
    ) -> Tuple[Optional[Tuple[str, str, str]], float]:
        from app.core.inference.model_router import model_router

        feat = signal.feature.replace("{keyword}", keyword)
        user_msg = f"Query: {keyword}\nFeature: {feat}\n\nPassage:\n{passage_text}"
        resp = await model_router.generate_text(
            system_prompt=REWRITE_SYSTEM,
            user_prompt=user_msg,
            model_override=model or None,
            max_tokens=600,
            temperature=0.2,
        )
        raw = resp.text if hasattr(resp, "text") else str(resp)
        cost = float(getattr(resp, "cost_usd", 0.0) or 0.0012)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip()).strip()
        try:
            data = json.loads(cleaned)
            w = str(data.get("with") or "").strip()
            wo = str(data.get("without") or "").strip()
            if w and wo:
                return (w, wo, "add"), cost
        except Exception:
            pass
        return None, cost

    async def run_stream(
        self,
        *,
        signal_id: str,
        keyword: str,
        target_url: str,
        passages: List[Passage],
        judge_model: str = "gemini-2.0-flash",
        rewrite_model: str = "gemini-2.0-flash",
        max_trials: int = MAX_TRIALS,
        concurrency: int = 4,
        is_byok: bool = False,
        byok_max_usd: Optional[float] = None,
        judge_fn: Optional[JudgeFn] = None,
        rewrite_fn: Optional[RewriteFn] = None,
        now: Optional[datetime] = None,
    ) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
        signal = get_signal(signal_id)
        if not signal:
            yield ("error", {"message": f"Unknown signal: {signal_id}"})
            return
        if len(passages) < 20:
            yield ("error", {"message": f"Passage pool too short ({len(passages)}; minimum 20 required)."})
            return

        ctx = SignalContext(keyword=keyword, now=now or datetime.now(timezone.utc))
        cap_n = min(max(20, max_trials), MAX_TRIALS, len(passages))
        reserved = 0.0 if is_byok else float(credit_cost_for_signal(signal))
        usd_cap = float(byok_max_usd if byok_max_usd is not None else BYOK_DEFAULT_MAX_USD)

        run_id = f"rs_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        j_fn = judge_fn or self._default_judge
        r_fn = rewrite_fn or self._default_rewrite

        yield (
            "start",
            {
                "run_id": run_id,
                "signal_id": signal.id,
                "signal_name": signal.name,
                "pool_size": len(passages),
                "max_n": cap_n,
                "billing_mode": "byok" if is_byok else "credits",
                "reserved_credits": reserved,
                "byok_cap_usd": usd_cap if is_byok else None,
            },
        )

        trials: List[RankSignalTrial] = []
        examples: List[RankSignalExample] = []
        rejected_pairs = 0
        skipped = 0
        cache_hits = 0
        cost_usd = 0.0
        cursor = 0
        checkpoints_read: set[int] = set()
        end_reason = "pool_exhausted"

        def _valid_count() -> int:
            return sum(1 for t in trials if t.outcome != "invalid")

        def _win_count() -> int:
            return sum(1 for t in trials if t.outcome == "win")

        async def _run_slot(p: Passage, side: str) -> Dict[str, Any]:
            nonlocal cache_hits
            if not is_eligible(signal, p.text, ctx):
                return {"kind": "skip", "cost": 0.0}

            cache_key = (p.hash, signal.id, keyword.strip().lower())
            slot_cost = 0.0
            if cache_key in self._pair_cache:
                w_text, wo_text, direction = self._pair_cache[cache_key]
                cache_hits += 1
            elif signal.build == "code" and signal.transform:
                transformed = signal.transform(p.text, ctx)
                if not transformed:
                    return {"kind": "skip", "cost": 0.0}
                w_text, wo_text, direction = transformed, p.text, "add"
                self._pair_cache[cache_key] = (w_text, wo_text, direction)
            else:
                built, rw_cost = await r_fn(signal, p.text, keyword, rewrite_model)
                slot_cost += rw_cost
                if not built:
                    return {"kind": "rejected", "cost": slot_cost}
                w_text, wo_text, direction = built
                ok, _ = check_pair(signal, w_text, wo_text, ctx)
                if not ok:
                    return {"kind": "rejected", "cost": slot_cost}
                self._pair_cache[cache_key] = (w_text, wo_text, direction)

            ok, _ = check_pair(signal, w_text, wo_text, ctx)
            if not ok:
                return {"kind": "rejected", "cost": slot_cost}

            a_text, b_text = (w_text, wo_text) if side == "A" else (wo_text, w_text)
            choice, j_cost = await j_fn(keyword, a_text, b_text, judge_model)
            slot_cost += j_cost
            outcome = "invalid" if choice is None else ("win" if choice == side else "loss")
            return {
                "kind": "trial",
                "cost": slot_cost,
                "trial": RankSignalTrial(
                    passage_hash=p.hash,
                    origin=p.origin,
                    direction=direction,
                    feature_side=side,
                    outcome=outcome,
                ),
                "example": RankSignalExample(
                    signal_id=signal.id,
                    direction=direction,
                    with_text=w_text,
                    without_text=wo_text,
                ),
            }

        while True:
            n_now = _valid_count()
            if n_now >= cap_n:
                end_reason = "max_trials"
                break
            if cursor >= len(passages):
                end_reason = "pool_exhausted"
                break
            if cost_usd >= usd_cap:
                end_reason = "budget"
                break

            next_stop = min(next((c for c in CHECKPOINTS if c > n_now), cap_n), cap_n)
            batch_size = min(max(1, concurrency), len(passages) - cursor, next_stop - n_now)

            on_a = sum(1 for t in trials if t.outcome != "invalid" and t.feature_side == "A")
            start_side = "A" if on_a <= (n_now - on_a) else "B"
            other_side = "B" if start_side == "A" else "A"

            batch = passages[cursor : cursor + batch_size]
            cursor += batch_size

            results = await asyncio.gather(
                *[_run_slot(p, start_side if idx % 2 == 0 else other_side) for idx, p in enumerate(batch)]
            )

            for r in results:
                cost_usd += r["cost"]
                if r["kind"] == "skip":
                    skipped += 1
                elif r["kind"] == "rejected":
                    rejected_pairs += 1
                elif r["kind"] == "trial":
                    trials.append(r["trial"])
                    if len(examples) < 2:
                        examples.append(r["example"])

            n_after = _valid_count()
            w_after = _win_count()
            yield (
                "progress",
                {
                    "n": n_after,
                    "wins": w_after,
                    "rejected_pairs": rejected_pairs,
                    "skipped": skipped,
                    "cache_hits": cache_hits,
                    "cost_usd": round(cost_usd, 6),
                },
            )

            crossed = [c for c in CHECKPOINTS if c <= n_after and c not in checkpoints_read]
            if crossed:
                for c in crossed:
                    checkpoints_read.add(c)
                v = verdict(w_after, n_after)
                yield ("checkpoint", {"n": n_after, "wins": w_after, "verdict": v})
                if v in ("positive", "negative"):
                    end_reason = "verdict"
                    break

        n_final = _valid_count()
        w_final = _win_count()
        post = posterior(w_final, n_final) if n_final > 0 else None
        final_verdict = verdict(w_final, n_final)

        # Proportional credit refund when stopping early or pool exhausted
        if is_byok:
            charged = 0.0
            refunded = 0.0
        else:
            frac = min(1.0, n_final / float(MAX_TRIALS)) if n_final > 0 else 0.0
            charged = round(reserved * max(0.5, frac) if n_final >= 20 else reserved * frac, 2)
            refunded = round(max(0.0, reserved - charged), 2)

        result = RankSignalResult(
            run_id=run_id,
            signal_id=signal.id,
            signal_name=signal.name,
            keyword=keyword,
            target_url=target_url,
            judge_model=judge_model,
            rewrite_model=rewrite_model,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            n_valid=n_final,
            wins=w_final,
            win_rate_mean=post.mean if post else None,
            ci_lo=post.lo if post else None,
            ci_hi=post.hi if post else None,
            verdict=final_verdict,
            end_reason=end_reason,
            rejected_pairs=rejected_pairs,
            skipped=skipped,
            cache_hits=cache_hits,
            credits=RankSignalCreditAccounting(
                billing_mode="byok" if is_byok else "credits",
                reserved_credits=reserved,
                charged_credits=charged,
                refunded_credits=refunded,
                estimated_llm_cost_usd=round(cost_usd, 6),
                byok_cap_usd=usd_cap if is_byok else None,
            ),
            trials=trials,
            examples=examples,
        )
        yield ("signal_done", result.model_dump(mode="json"))


rank_signal_runner = RankSignalRunner()
