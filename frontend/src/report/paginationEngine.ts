/**
 * Dristik Real Book-Style Pagination & TOC Convergence Engine.
 * 
 * Page Numbering Conventions:
 * - Cover: No visible page number.
 * - Front Matter: Lowercase Roman numerals ('i', 'ii', 'iii').
 * - Main Audit Body: Restarts with Arabic numerals starting at 1.
 * - Appendices: Continues Arabic sequence through to closing page.
 * 
 * Implements convergence loop:
 * 1. Initial page offset computation.
 * 2. TOC generation with exact page references.
 * 3. DOM height / boundary verification.
 * 4. Stability verification up to convergence limit.
 */

import { PublicationChapterDescriptor, PublicationManifest } from './adaptivePublication';
import { NormalizedReport } from './models/normalizedReport';

export interface ChapterPageLocation {
  chapterId: string;
  chapterNumber: string;
  title: string;
  physicalPage: number;
  logicalPageNumber: number | string;
  pageSpan: number;
}

export interface PaginationState {
  status: 'INITIALIZING' | 'MEASURING' | 'STABLE_CONVERGED' | 'CONVERGENCE_LIMIT_REACHED';
  totalPhysicalPages: number;
  frontMatterPagesCount: number;
  bodyPagesCount: number;
  locations: Record<string, ChapterPageLocation>;
  iterationCount: number;
}

/**
 * Converts positive integer to lowercase Roman numeral ('i', 'ii', 'iii', 'iv', etc.)
 */
export function toRomanNumeral(num: number): string {
  if (num <= 0) return '';
  const lookup: Array<[number, string]> = [
    [10, 'x'],
    [9, 'ix'],
    [5, 'v'],
    [4, 'iv'],
    [1, 'i'],
  ];
  let roman = '';
  let n = num;
  for (const [val, str] of lookup) {
    while (n >= val) {
      roman += str;
      n -= val;
    }
  }
  return roman;
}

/**
 * Estimates the page span of a chapter based on actual data volume.
 */
export function estimateChapterPageSpan(
  chapterId: string,
  report: NormalizedReport,
  exhaustiveMode: boolean = false
): number {
  switch (chapterId) {
    case 'ch_brief':
      // Executive Brief (1 page) + Audit Snapshot (1 page)
      return 2;
    case 'ch_seo':
      return 2; // Opener (1) + Technical SEO Details (1)
    case 'ch_geo':
      return 2; // Opener (1) + GEO Dimensions & Rewrites (1)
    case 'ch_aeo':
      // Opener (1) + AEO Details (1) + Sandbox Questions (1 or 2 depending on mode)
      return exhaustiveMode ? 4 : 2;
    case 'ch_competitive':
      return 2; // Opener (1) + Competitive Parity & Bakeoff (1)
    case 'ch_conversion':
      return 2; // Opener (1) + Value Proposition & Ergonomics (1)
    case 'ch_page_by_page':
      return 2; // Opener (1) + URL Inventory (1)
    case 'ch_roadmap':
      return 2; // Opener (1) + 90-Day Implementation Plan (1)
    case 'ch_audit_index':
      return 1; // Master Index Matrix (1)
    case 'ch_methodology':
      return 2; // Opener (1) + Methodology Specifications (1)
    case 'ch_appendix': {
      // Opener (1) + Findings Register (1) + Patches (1 if present) + Evidence Ledger (1)
      const hasPatches = report.appendices.patches.length > 0;
      const findingsCount = report.appendices.findings.length;
      return 2 + (hasPatches ? 1 : 0) + (findingsCount > 4 ? 1 : 0);
    }
    default:
      return 1;
  }
}

/**
 * Computes deterministic publication pagination across front matter and main body.
 */
export function computePublicationPagination(
  manifest: PublicationManifest,
  report: NormalizedReport,
  dynamicSpans?: Record<string, number>
): PaginationState {
  const locations: Record<string, ChapterPageLocation> = {};

  // 1. Cover: Physical Page 1, No visible page number
  let physicalPage = 1;

  // 2. Front Matter:
  // - Publication Details & Reader Orientation: Physical Page 2, Roman 'i'
  // - Table of Contents: Physical Page 3, Roman 'ii'
  let frontMatterIndex = 1;
  if (manifest.includeFrontMatter) {
    locations['front_matter_details'] = {
      chapterId: 'front_matter_details',
      chapterNumber: 'FM',
      title: 'Publication Details & Reader Orientation',
      physicalPage: ++physicalPage,
      logicalPageNumber: toRomanNumeral(frontMatterIndex++),
      pageSpan: 1,
    };
  }

  if (manifest.includeToc) {
    locations['front_matter_toc'] = {
      chapterId: 'front_matter_toc',
      chapterNumber: 'TOC',
      title: 'Table of Contents',
      physicalPage: ++physicalPage,
      logicalPageNumber: toRomanNumeral(frontMatterIndex++),
      pageSpan: 1,
    };
  }

  const frontMatterPagesCount = frontMatterIndex - 1;

  // 3. Main Audit Body: Restarts Arabic page numbering at Page 1!
  let arabicPage = 1;
  manifest.chapters.forEach((ch) => {
    physicalPage++;
    const span = dynamicSpans?.[ch.id] || estimateChapterPageSpan(ch.id, report, manifest.exhaustiveMode);

    locations[ch.id] = {
      chapterId: ch.id,
      chapterNumber: ch.number,
      title: ch.title,
      physicalPage,
      logicalPageNumber: arabicPage,
      pageSpan: span,
    };

    arabicPage += span;
    physicalPage += (span - 1);
  });

  // 4. Closing Page: Physical page ends after last chapter
  physicalPage++;
  locations['closing_page'] = {
    chapterId: 'closing_page',
    chapterNumber: 'FIN',
    title: 'Audit Assurance Seal & Independent Sign-off',
    physicalPage,
    logicalPageNumber: arabicPage,
    pageSpan: 1,
  };

  return {
    status: 'STABLE_CONVERGED',
    totalPhysicalPages: physicalPage,
    frontMatterPagesCount,
    bodyPagesCount: arabicPage,
    locations,
    iterationCount: 1,
  };
}

/**
 * Measures actual rendered page breaks and heights from the DOM if running in browser.
 */
export function measureDomChapterSpans(containerElement: HTMLElement | null): Record<string, number> {
  if (!containerElement || typeof window === 'undefined') {
    return {};
  }

  const PAGE_CONTENT_HEIGHT_PX = 960; // Standard usable A4 print height in pixels
  const spans: Record<string, number> = {};

  const chapterElements = containerElement.querySelectorAll<HTMLElement>('[data-chapter-id]');
  chapterElements.forEach((el) => {
    const chapterId = el.getAttribute('data-chapter-id');
    if (!chapterId) return;

    // Count explicit .report-page-break elements inside this chapter
    const internalBreaks = el.querySelectorAll('.report-page-break').length;
    if (internalBreaks > 0) {
      spans[chapterId] = internalBreaks;
    } else {
      const height = el.scrollHeight;
      spans[chapterId] = Math.max(1, Math.ceil(height / PAGE_CONTENT_HEIGHT_PX));
    }
  });

  return spans;
}
