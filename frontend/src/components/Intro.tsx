import React from 'react';
import { Card, Section } from './ui';

const STEPS = [
  {
    n: '01',
    title: 'Scan the live site',
    body: 'Paste a public URL. Dristik reads headlines, pricing, proof, and structure the way a buyer and a search engine would.',
  },
  {
    n: '02',
    title: 'Test buyer questions',
    body: 'We check how clearly the site answers what you sell, who it is for, pricing, alternatives, trust, and results.',
  },
  {
    n: '03',
    title: 'Ship the fixes',
    body: 'You get a score, ranked findings, a 7 / 30 / 90-day plan, and drop-in code your developer can install.',
  },
];

const SCORES = [
  { title: 'Human', body: 'Can a visitor tell what you sell, at what price, and what to do next in five seconds?' },
  { title: 'Search', body: 'Can search engines discover and understand the pages we checked?' },
  { title: 'AI readiness', body: 'Can an answer engine extract what you offer from the pages we checked? Live citations are a separate measurement and remain unmeasured until the relevant engines are actually queried.' },
];

const FITS = [
  { title: 'SaaS & software', body: 'Pricing, ICP, and competitor comparisons that AI can quote.' },
  { title: 'Agencies & services', body: 'Proof, credentials, and a clear reason to enquire.' },
  { title: 'Commerce & local', body: 'Products, reviews, and trust signals that engines can extract.' },
];

export function Intro() {
  return (
    <div className="space-y-16 pt-4">
      <div className="text-center max-w-3xl mx-auto space-y-3 pt-4 pb-2">
        <p className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-pine/10 text-pine border border-pine/20 tracking-wide">
          <span>Enterprise Website Intelligence</span>
        </p>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-[-0.035em] text-ink leading-tight">
          Clarity for Search, AI Engines, and Conversion.
        </h2>
        <p className="text-base sm:text-lg text-ink-500 max-w-2xl mx-auto leading-relaxed">
          Evidence-backed audits for modern search and answer engines. Zero guesswork.
        </p>
      </div>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {STEPS.map((step) => (
          <div
            key={step.n}
            className="card p-6 rounded-[22px] bg-paper-50 border border-line/80 shadow-[0_4px_20px_rgba(0,0,0,0.03)] hover:shadow-[0_12px_36px_rgba(0,0,0,0.07)] transition-all duration-300 flex flex-col justify-between"
          >
            <div>
              <span className="inline-block px-2.5 py-1 rounded-full text-[11px] font-semibold bg-paper-200/80 text-ink-700 tracking-wider mb-4">
                STEP {step.n}
              </span>
              <h3 className="text-xl font-semibold text-ink tracking-[-0.02em]">{step.title}</h3>
              <p className="mt-2.5 text-sm text-ink-500 leading-relaxed">{step.body}</p>
            </div>
          </div>
        ))}
      </section>

      <Section
        title="Three ways to assess readiness"
        description="Scores are based on the audit evidence and pages checked. Traffic, revenue impact, and live AI citations are verified measurements—not assumptions."
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {SCORES.map((score) => (
            <div
              key={score.title}
              className="card p-6 rounded-[22px] bg-paper-50 border border-line/80 shadow-[0_4px_20px_rgba(0,0,0,0.03)] hover:shadow-[0_12px_36px_rgba(0,0,0,0.07)] transition-all duration-300"
            >
              <h3 className="text-lg font-semibold text-ink tracking-[-0.02em]">{score.title}</h3>
              <p className="mt-2 text-sm text-ink-500 leading-relaxed">{score.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Engineered for industry leaders">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {FITS.map((item) => (
            <div
              key={item.title}
              className="card p-6 rounded-[22px] bg-paper-50 border border-line/80 shadow-[0_4px_20px_rgba(0,0,0,0.03)] hover:shadow-[0_12px_36px_rgba(0,0,0,0.07)] transition-all duration-300"
            >
              <h3 className="text-lg font-semibold text-ink tracking-[-0.02em]">{item.title}</h3>
              <p className="mt-2 text-sm text-ink-500 leading-relaxed">{item.body}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
