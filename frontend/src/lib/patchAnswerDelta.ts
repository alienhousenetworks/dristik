/**
 * A suggested after-patch answer counts only when it states a new fact.
 * The same sentence, a current meta description, or another
 * "cannot determine" is not a citation gain.
 */

const UNANSWERED =
  /cannot determine|cannot answer|not available|not explicitly stated|not clearly stated|no direct statements|not stated on/i;
const EXISTING_PAGE =
  /as stated in (?:their|the|its) (?:meta description|title tag|title|homepage|h1)/i;
const PROMISED_NOT_STATED = /will be cited|will cite|grounded response will/i;

function normalizeAnswer(text: string): string {
  return text
    .replace(/\[[^\]]+\]/g, ' ')
    .replace(/,?\s*as stated in (?:their|the|its) [^.]{0,80}/gi, ' ')
    .replace(/,?\s*according to (?:their|the|its) [^.]{0,80}/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
    .replace(/[.,;:]+$/g, '')
    .replace(/^[.,;:]+/g, '');
}

export function answersUnchanged(before?: string | null, after?: string | null): boolean {
  if (!(before || '').trim() || !(after || '').trim()) return false;
  if (PROMISED_NOT_STATED.test(after || '') && !EXISTING_PAGE.test(after || '')) return true;
  if (EXISTING_PAGE.test(after || '')) return true;
  if (UNANSWERED.test(before || '') && UNANSWERED.test(after || '')) return true;
  const left = normalizeAnswer(before || '');
  const right = normalizeAnswer(after || '');
  if (!left || !right || left === right) return true;
  if (right.startsWith(left) || left.startsWith(right)) {
    const extra = (right.startsWith(left) ? right.slice(left.length) : left.slice(right.length))
      .trim()
      .replace(/^[.,;:]+/, '');
    if (!extra || UNANSWERED.test(extra)) return true;
  }
  return false;
}

export interface PatchScoreInput {
  before_score: number;
  after_score?: number | null;
  before_answer?: string | null;
  after_answer?: string | null;
  patch_citation_gain?: number | null;
}

export function effectiveAfterScore(item: PatchScoreInput): number | null {
  if (item.after_score == null && !(item.after_answer || '').trim()) return null;
  if (answersUnchanged(item.before_answer, item.after_answer)) return item.before_score;
  return item.after_score ?? null;
}

export function effectiveCitationGain(item: PatchScoreInput): number | null {
  if (answersUnchanged(item.before_answer, item.after_answer)) return null;
  if (item.after_score == null || item.after_score <= item.before_score) return null;
  return item.patch_citation_gain ?? null;
}
