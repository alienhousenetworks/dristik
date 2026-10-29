import { describe, expect, it } from 'vitest';
import { sandboxAnswers } from './sandboxAnswers';

const cloudQuote =
  'Cloud Solutions Secure, scalable, and cost-efficient cloud infrastructure designed to power modern digital products and enterprise workloads. We work closely with leadership teams to analyze current processes, identify gaps, and design practical, results-driven solutions.';

describe('sandbox answers', () => {
  it('shows the current passage and a knowledge-base answer for a stored quote card', () => {
    const answers = sandboxAnswers({
      generated_question: 'Who is the target buyer for AlienHouse Networks?',
      answerability_status: 'ANSWERABLE',
      grounding_ratio: 1,
      crawled_answer: `According to AlienHouse Networks's crawled pages: "${cloudQuote}"`,
      recommended_answer:
        'AlienHouse Networks is well-positioned to answer this inquiry with existing content. Schema markup will improve structured citation.',
      section_update_recommendation:
        'Add Schema.org JSON-LD structured data markup to /about (## Target Audience & Disqualification Criteria) to accelerate AI answer engine citations.',
      gap_analysis:
        'Strong first-party evidence found for AlienHouse Networks. Adding structured JSON-LD Schema.org markup will further elevate extractability.',
      source_page_title: 'ALIENHOUSE NETWORKS | Hyper-Advanced Digital Ecosystems',
      source_section: 'BEYOND IMAGINATION',
      source_url: 'https://alienhousenetworks.com',
      claim_decomposition: [
        {
          status: 'SUPPORTED',
          claim_text:
            'According to AlienHouse Networks\'s crawled pages: "Cloud Solutions Secure, scalable, and cost-efficient cloud infrastructure designed to power modern digital products and enterprise workloads.',
        },
        {
          status: 'SUPPORTED',
          claim_text:
            'We work closely with leadership teams to analyze current processes, identify gaps, and design practical, results-driven solutions.',
        },
      ],
    });

    expect(answers.currentExtract).toContain('Cloud Solutions Secure');
    expect(answers.currentExtract).not.toMatch(/according to/i);
    expect(answers.ragAnswer).toContain('Cloud Solutions Secure');
    expect(answers.ragAnswer).toContain('leadership teams');
    expect(answers.ragAnswer).toContain('Source: ALIENHOUSE NETWORKS');
    expect(answers.ragAnswer).toContain('https://alienhousenetworks.com');
    expect(answers.ragAnswer).not.toMatch(/schema\.org|json-ld/i);
    expect(answers.abstained).toBe(false);
    expect(answers.contentBrief).toBeNull();
    expect(answers.gapNote).toBe('Every claim in the knowledge-base answer matches a retrieved passage.');
  });

  it('uses a stored knowledge-base answer when the report already has one', () => {
    const answers = sandboxAnswers({
      answerability_status: 'ANSWERABLE',
      grounding_ratio: 0.9,
      crawled_answer: 'Pricing starts at $99 per cluster per month.',
      rag_answer: 'Pricing starts at $99 per cluster per month. Source: Pricing Plans (https://acme.example/pricing).',
      recommended_answer: 'Add Schema.org JSON-LD to /pricing to accelerate AI answer engine citations.',
    });

    expect(answers.currentExtract).toBe('Pricing starts at $99 per cluster per month.');
    expect(answers.ragAnswer).toContain('Source: Pricing Plans');
    expect(answers.ragAnswer).not.toMatch(/json-ld/i);
    expect(answers.abstained).toBe(false);
  });

  it('abstains when the crawl does not state the fact', () => {
    const answers = sandboxAnswers({
      answerability_status: 'EVIDENCE_GAP',
      grounding_ratio: 0,
      crawled_answer: 'Pricing information for Mysterious Agency is not published on crawled website pages.',
      recommended_answer: 'Mysterious Agency offers structured packaging starting from a published base tier.',
      section_update_recommendation:
        "Update /pricing under section '## Published Pricing Tiers & Billing Structure': Publish a dedicated pricing tier card.",
    });

    expect(answers.abstained).toBe(true);
    expect(answers.ragAnswer).toMatch(/not published/i);
    expect(answers.ragAnswer).not.toMatch(/published base tier/i);
    expect(answers.contentBrief).toMatch(/Update \/pricing/);
  });
});
