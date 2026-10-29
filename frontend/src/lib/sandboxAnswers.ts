/**
 * Each sandbox question has two texts:
 * the passage retrieved from the crawl, and an answer written only from that passage.
 * A stored report may only have the passage inside crawled_answer and a schema
 * sentence in recommended_answer. Those schema sentences are not answers.
 */

export interface SandboxAnswerInput {
  crawled_answer?: string | null;
  rag_answer?: string | null;
  recommended_answer?: string | null;
  generated_question?: string | null;
  answerability_status?: string | null;
  evidence_snippet?: string | null;
  evidence_url?: string | null;
  source_url?: string | null;
  source_page_title?: string | null;
  source_section?: string | null;
  claim_decomposition?: Array<{ claim_text?: string | null; status?: string | null }> | null;
  missing_aspects?: string[] | null;
  grounding_ratio?: number | null;
  gap_analysis?: string | null;
  section_update_recommendation?: string | null;
}

export interface SandboxAnswers {
  currentExtract: string;
  ragAnswer: string;
  abstained: boolean;
  citation: string | null;
  contentBrief: string | null;
  gapNote: string | null;
}

const ABSTAIN =
  /cannot determine|cannot answer|not available|not explicitly stated|not clearly stated|not published|not disclosed|not discovered|not declared|was not discovered|do not state|does not state|does not contain/i;

const BOILERPLATE =
  /schema\.org|json-ld|schema markup|well-positioned to answer|accelerate ai answer|elevate extractability|standalone faq|structured citation|will further elevate/i;

export function isCitationBoilerplate(text: string | null | undefined): boolean {
  if (!text || !text.trim()) return false;
  return BOILERPLATE.test(text);
}

export function isAbstention(text: string | null | undefined): boolean {
  if (!text || !text.trim()) return true;
  return ABSTAIN.test(text);
}

function clean(text: string): string {
  return text.replace(/\s+/g, ' ').replace(/^["']+|["']+$/g, '').trim();
}

function unwrapPassage(raw: string): string {
  const wrapped = raw.match(/according to .+?crawled pages:\s*"([\s\S]+)/i);
  if (wrapped) return clean(wrapped[1]);
  const partial = raw.match(/partially referenced on .+?:\s*"([\s\S]+)/i);
  if (partial) return clean(partial[1].replace(/\bbut lacks[\s\S]*$/i, ''));
  return clean(raw);
}

export function currentPageExtract(item: SandboxAnswerInput): string {
  return unwrapPassage(item.crawled_answer || '');
}

export function citationLine(item: SandboxAnswerInput): string {
  const title = item.source_page_title?.trim();
  const section = item.source_section?.trim();
  const url = (item.source_url || item.evidence_url || '').trim();
  const place = [title, section ? `section ${section}` : ''].filter(Boolean).join(', ');
  if (place && url) return `Source: ${place} (${url}).`;
  if (place) return `Source: ${place}.`;
  if (url) return `Source: ${url}.`;
  return '';
}

function addSentence(out: string[], text: string) {
  const key = text.toLowerCase();
  if (key.length < 15) return;
  for (let i = 0; i < out.length; i += 1) {
    const prev = out[i].toLowerCase();
    if (prev.includes(key)) return;
    if (key.includes(prev)) {
      out[i] = text;
      return;
    }
  }
  out.push(text);
}

function supportedSentences(item: SandboxAnswerInput): string[] {
  const out: string[] = [];
  for (const claim of item.claim_decomposition || []) {
    if (claim.status !== 'SUPPORTED' && claim.status !== 'PARTIALLY_SUPPORTED') continue;
    const text = unwrapPassage(claim.claim_text || '');
    if (!text || isAbstention(text) || isCitationBoilerplate(text)) continue;
    const sentence = /[.!?]$/.test(text) ? text : `${text}.`;
    addSentence(out, sentence);
  }
  return out;
}

function isGap(status: string | null | undefined): boolean {
  return status === 'EVIDENCE_GAP' || status === 'UNANSWERABLE' || status === 'CONFLICTING';
}

export function contentBrief(item: SandboxAnswerInput): string | null {
  const grounded =
    item.answerability_status === 'ANSWERABLE' && (item.grounding_ratio ?? 0) >= 0.7;
  if (grounded) return null;
  const rec = (item.section_update_recommendation || '').trim();
  if (!rec || isCitationBoilerplate(rec) || /no new fact is required/i.test(rec)) return null;
  return rec;
}

export function gapNote(item: SandboxAnswerInput): string | null {
  const raw = (item.gap_analysis || '').trim();
  if (!raw) return null;
  if (isCitationBoilerplate(raw)) {
    if ((item.grounding_ratio ?? 0) >= 0.7) {
      return 'Every claim in the knowledge-base answer matches a retrieved passage.';
    }
    return null;
  }
  return raw;
}

export function sandboxAnswers(item: SandboxAnswerInput): SandboxAnswers {
  const current = currentPageExtract(item);
  const cite = citationLine(item);
  const storedRag = (item.rag_answer || '').trim();
  const gap = isGap(item.answerability_status);
  const currentAbstains = isAbstention(current) || isAbstention(item.crawled_answer);

  let rag = '';
  let abstained = false;

  if (storedRag && !isCitationBoilerplate(storedRag)) {
    rag = storedRag;
    abstained = isAbstention(storedRag);
  } else if (gap || currentAbstains) {
    rag = (item.crawled_answer || '').trim() || 'The crawled knowledge base does not contain a fact that answers this question.';
    abstained = true;
  } else {
    const sentences = supportedSentences(item);
    const body = sentences.length ? sentences.join(' ') : current;
    const missing = (item.missing_aspects || [])
      .map((aspect) => aspect.trim())
      .filter((aspect) => aspect.length > 8 && aspect !== (item.generated_question || '').trim());
    rag = body;
    if (item.answerability_status === 'PARTIAL' && missing.length) {
      rag += ` The crawl does not state: ${missing.join('; ')}.`;
    }
    if (cite && !rag.includes('Source:')) {
      rag += ` ${cite}`;
    }
    abstained = false;
  }

  const showCitation = !abstained && Boolean(cite);
  return {
    currentExtract: current || 'No passage on the crawled pages states this.',
    ragAnswer: rag,
    abstained,
    citation: showCitation ? cite : null,
    contentBrief: contentBrief(item),
    gapNote: gapNote(item),
  };
}
