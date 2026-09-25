import React, { useState, useEffect } from 'react';

interface FlowNodeInfo {
  id: string;
  title: string;
  category: string;
  simpleExplanation: string;
  whyItMatters: string;
  dristikAction: string;
}

const NODE_DETAILS: Record<string, FlowNodeInfo> = {
  claude: {
    id: 'claude',
    title: 'Neural Reasoning & Synthesis',
    category: 'Cognitive Reasoning Agent',
    simpleExplanation: 'High-ticket B2B buyers and enterprise executives use deep reasoning AI models to analyze vendor credibility, certifications, and customer case studies.',
    whyItMatters: 'If trust badges, case studies, or official registrations (GSTIN/CIN/SOC2) are missing from your code, reasoning models flag your business as unverified.',
    dristikAction: 'We spot missing trust proof and structure your official credentials into AI-approved semantic schemas.',
  },
  chatgpt: {
    id: 'chatgpt',
    title: 'Autonomous Buyer & Decision Agent',
    category: 'Commercial Decision Agent',
    simpleExplanation: 'Commercial buyers ask autonomous conversational AI agents: "What is the best tool for my business, and how much does it cost?"',
    whyItMatters: 'If your pricing or core offer is buried in marketing buzzwords, buyer agents skip your site or cite outdated details.',
    dristikAction: 'We test the exact queries autonomous buyer agents run and generate the digital tags needed to get cited accurately.',
  },
  perplexity: {
    id: 'perplexity',
    title: 'Real-Time Citation Synthesizer',
    category: 'Live Research Engine',
    simpleExplanation: 'Autonomous search agents comb the live web in real time and synthesize comprehensive answers with verified source citations.',
    whyItMatters: 'If your competitor has clear comparison FAQs and you do not, citation engines recommend your competitor instead of you.',
    dristikAction: 'We run direct head-to-head audits and give you the semantic FAQ answers that citation engines love to quote.',
  },
  google: {
    id: 'google',
    title: 'Semantic Discovery & Overview Engine',
    category: 'Search Discovery Engine',
    simpleExplanation: 'Modern search engines deploy AI Overviews and answer bots at the very top of search results before normal blue links.',
    whyItMatters: 'If your site lacks clean digital identity code (Schema.org AST), discovery bots skip your page when generating AI summaries.',
    dristikAction: 'We generate complete, zero-error Schema.org tags your web developer can paste in under 15 minutes.',
  },
  control_plane: {
    id: 'control_plane',
    title: 'Dristik AI Control Plane',
    category: 'Automated Evaluation Engine',
    simpleExplanation: 'Dristik acts as an automated security and intelligence gateway between AI answer engines and your live website.',
    whyItMatters: 'Other tools guess or hallucinate. Dristik verifies actual live DOM facts with cryptographic evidence, eliminating phantom warnings.',
    dristikAction: 'Filters out 60 useless warnings, isolates the 1 single bottleneck costing you customers, and creates the exact code patches to fix it.',
  },
  codepack: {
    id: 'codepack',
    title: 'Ready-to-Use Code Pack (ZIP)',
    category: 'Governed Deliverable',
    simpleExplanation: 'A single 1-click download folder containing production-ready code files made specifically for your website.',
    whyItMatters: 'Most audits give you a 40-page PDF that collects dust. Dristik gives you the actual code your developer can install in 15 minutes.',
    dristikAction: 'Includes schema.jsonld, semantic faq.html, metadata.html tags, and a plain-English 1-page guide for your web designer.',
  },
  scores: {
    id: 'scores',
    title: 'The 3 Honest Scores (0–100)',
    category: 'Governed Measurement',
    simpleExplanation: 'Clear grades for Human Ease of Use, Google Search Code, and AI Citation Readiness.',
    whyItMatters: 'We never invent fake revenue numbers or fake CAC metrics. Every score is based strictly on verified facts on your website.',
    dristikAction: 'Tells you clearly: where you are strong, what is holding you back, and exactly what minor tasks to ignore this month.',
  },
  battlecard: {
    id: 'battlecard',
    title: '1-on-1 Competitor Battlecard',
    category: 'Governed Intelligence',
    simpleExplanation: 'A side-by-side comparison showing what AI says when buyers compare you against your #1 competitor.',
    whyItMatters: 'Reveals the exact questions where your rival is stealing your leads, so you can fix your answers and win them back.',
    dristikAction: 'Gives your sales and marketing team an unfair advantage with verified strengths vs. trade-offs.',
  },
  requery: {
    id: 'requery',
    title: 'Before → After Citability Evaluation',
    category: 'Governed Verification',
    simpleExplanation: 'Evaluates citation readiness across commercial buyer inquiries before and after applying structured entity patches.',
    whyItMatters: 'Provides evidence-backed before/after measurement for founders and leadership, eliminating guesswork and hype.',
    dristikAction: 'Measures verified citability gains across commercial queries after confirmed patch deployment.',
  },
};

const AUDIT_STREAM_EVENTS = [
  { status: 'allow', action: 'tool.call → live.sitemap.crawl', detail: '24 pages scanned' },
  { status: 'block', action: 'pii.export → ungrounded.claims', detail: 'filtered' },
  { status: 'alert', action: 'buyer.agent → missing.pricing', detail: 'tier unknown' },
  { status: 'alert', action: 'citation.scan → rival.steals.icp', detail: 'recommend rival' },
  { status: 'patch', action: 'generate.patch → schema.jsonld', detail: '15-min drop-in' },
  { status: 'allow', action: 'requery.evaluate → verified.gain', detail: 'Evidence-Backed' },
];


export function AnimatedPipelineFlow() {
  const [selectedNode, setSelectedNode] = useState<string>('control_plane');
  const [activeTab, setActiveTab] = useState<'IDENTITY' | 'POLICY'>('POLICY');
  const [streamIndex, setStreamIndex] = useState(0);

  // Auto-advance stream ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setStreamIndex((prev) => (prev + 1) % AUDIT_STREAM_EVENTS.length);
    }, 2200);
    return () => clearInterval(timer);
  }, []);

  const currentNode = NODE_DETAILS[selectedNode] || NODE_DETAILS.control_plane;

  return (
    <div className="w-full my-8 bg-paper-100 border border-line rounded-2xl p-4 sm:p-7 shadow-sm text-ink overflow-hidden relative font-sans">
      {/* Background warm radial glow matching website theme */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage: `
            radial-gradient(circle at 50% 0%, rgba(31, 61, 54, 0.08) 0%, transparent 65%),
            radial-gradient(circle at 10% 50%, rgba(168, 132, 78, 0.06) 0%, transparent 40%),
            radial-gradient(circle at 90% 50%, rgba(31, 61, 54, 0.06) 0%, transparent 40%)
          `,
        }}
      />
      {/* Subtle Dot Grid Matrix in website pine green */}
      <div 
        className="absolute inset-0 opacity-[0.05] pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, #1f3d36 1px, transparent 0)`,
          backgroundSize: '20px 20px',
        }}
      />

      {/* Top Header bar */}
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-6 border-b border-line">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-pine shadow-[0_0_6px_rgba(31,61,54,0.4)] animate-pulse" />
            <span className="font-mono text-[11px] text-pine uppercase tracking-widest font-semibold">
              Live Architecture Flow · Branching Engine
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-serif text-ink tracking-tight mt-1">
            How Dristik Audits & Governs Your Digital Footprint
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-paper-50 border border-line text-xs font-mono text-ink-700 shadow-2xs">
            <span className="w-1.5 h-1.5 rounded-full bg-good animate-ping" />
            <span>Click any node to inspect</span>
          </div>
        </div>
      </div>

      {/* ================= TOP LEVEL ROW: SOURCE & IDENTITY ================= */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-12 gap-4 pt-6 pb-2">
        {/* Top-Left Box: YOUR SOURCE */}
        <div className="md:col-span-4 p-3 rounded-xl border border-line bg-paper-50 text-xs font-mono">
          <div className="text-[10px] text-ink-500 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>YOUR WEBSITE SOURCE</span>
            <span className="text-good font-semibold">HTTPS CRAWL</span>
          </div>
          <div className="flex items-center gap-1.5 text-ink-700">
            <span className="px-2 py-0.5 rounded bg-paper-200 border border-line text-[11px]">Homepage</span>
            <span className="px-2 py-0.5 rounded bg-paper-200 border border-line text-[11px]">Pricing</span>
            <span className="px-2 py-0.5 rounded bg-paper-200 border border-line text-[11px]">Sitemap</span>
          </div>
        </div>

        {/* Top-Center/Right Box: YOUR IDENTITY & SCHEMAS */}
        <div className="md:col-span-8 p-3 rounded-xl border border-line bg-paper-50 text-xs font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="text-[10px] text-ink-500 uppercase tracking-wider mb-1">
              YOUR DIGITAL IDENTITY & SCHEMAS
            </div>
            <div className="flex flex-wrap items-center gap-2 text-ink-700">
              <span className="flex items-center gap-1 text-[11px] text-pine font-medium">
                <span className="text-good font-bold">❖</span> Organization
              </span>
              <span className="text-ink-300">·</span>
              <span className="flex items-center gap-1 text-[11px] text-pine font-medium">
                <span className="text-good font-bold">❖</span> PriceSpecification
              </span>
              <span className="text-ink-300">·</span>
              <span className="flex items-center gap-1 text-[11px] text-pine font-medium">
                <span className="text-good font-bold">❖</span> FAQ & Audience AST
              </span>
            </div>
          </div>
          <span className="text-[10px] text-pine font-mono px-2 py-0.5 rounded bg-pine/10 border border-pine/20 font-medium whitespace-nowrap">
            EVIDENCE VERIFIED
          </span>
        </div>
      </div>

      {/* Top connector line pointing into center */}
      <div className="relative z-10 hidden md:flex items-center justify-center my-1">
        <div className="flex flex-col items-center">
          <span className="text-[9px] font-mono text-ink-500 tracking-widest uppercase mb-0.5">
            TEAMS & DIGITAL SIGNALS
          </span>
          <div className="w-[1.5px] h-6 bg-pine/40 relative">
            <div className="w-1.5 h-1.5 rounded-full bg-pine absolute -bottom-1 -left-[2px] shadow-[0_0_4px_rgba(31,61,54,0.4)]" />
          </div>
        </div>
      </div>

      {/* ================= MAIN 3-ZONE BRANCHING FLOW ================= */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-2 lg:gap-0 items-center pt-2">

        {/* ================= ZONE 1: LEFT (YOUR FLEET / AI ENGINES) ================= */}
        <div className="lg:col-span-4">
          <div className="border border-line rounded-xl p-3.5 bg-paper-50 relative shadow-2xs">
            {/* Box Header */}
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <span className="font-mono text-[10px] text-ink-500 uppercase tracking-widest font-semibold">
                YOUR FLEET · AI BUYER AGENTS
              </span>
              <span className="text-[9px] font-mono text-pine bg-pine/10 px-2 py-0.5 rounded border border-pine/20 font-semibold">
                ACTIVE
              </span>
            </div>

            {/* 4 Agent Cards */}
            <div className="space-y-2.5 mt-3">
              {/* Neural Reasoner */}
              <button
                type="button"
                onClick={() => setSelectedNode('claude')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'claude'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded flex items-center justify-center text-[#9a4b24] font-bold text-xs bg-amber-50 border border-amber-200">
                      ✦
                    </div>
                    <div>
                      <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                        REASONING · AGENT
                      </div>
                      <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors">
                        NEURAL REASONER
                      </div>
                    </div>
                  </div>
                  <span className="w-2 h-2 rounded-sm bg-ink-300 group-hover:bg-pine transition-colors" />
                </div>
              </button>

              {/* Autonomous Buyer */}
              <button
                type="button"
                onClick={() => setSelectedNode('chatgpt')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'chatgpt'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded flex items-center justify-center text-good font-bold text-xs bg-emerald-50 border border-emerald-200">
                      ✳
                    </div>
                    <div>
                      <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                        DECISION · AGENT
                      </div>
                      <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors">
                        AUTONOMOUS BUYER
                      </div>
                    </div>
                  </div>
                  <span className="w-2 h-2 rounded-sm bg-ink-300 group-hover:bg-pine transition-colors" />
                </div>
              </button>

              {/* Citation Synthesizer */}
              <button
                type="button"
                onClick={() => setSelectedNode('perplexity')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'perplexity'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded flex items-center justify-center text-sky-700 font-bold text-xs bg-sky-50 border border-sky-200">
                      ⌘
                    </div>
                    <div>
                      <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                        RESEARCH · AGENT
                      </div>
                      <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors">
                        CITATION SYNTHESIZER
                      </div>
                    </div>
                  </div>
                  <span className="w-2 h-2 rounded-sm bg-ink-300 group-hover:bg-pine transition-colors" />
                </div>
              </button>

              {/* Semantic Discovery */}
              <button
                type="button"
                onClick={() => setSelectedNode('google')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'google'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded flex items-center justify-center text-indigo-700 font-bold text-xs bg-indigo-50 border border-indigo-200">
                      ◈
                    </div>
                    <div>
                      <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                        DISCOVERY · AGENT
                      </div>
                      <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors">
                        SEMANTIC DISCOVERY
                      </div>
                    </div>
                  </div>
                  <span className="w-2 h-2 rounded-sm bg-ink-300 group-hover:bg-pine transition-colors" />
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* ================= SVG BRANCH CONNECTOR: LEFT -> CENTER ================= */}
        <div className="hidden lg:flex lg:col-span-1 h-72 items-center justify-center relative">
          <svg className="w-full h-full" viewBox="0 0 100 240" fill="none" preserveAspectRatio="none">
            {/* Trunk line from convergence to center */}
            <path
              d="M 50 120 L 100 120"
              stroke="#1f3d36"
              strokeWidth="2"
              strokeOpacity="0.45"
            />
            {/* Vertical spine connecting the 4 branches */}
            <path
              d="M 50 30 L 50 210"
              stroke="#1f3d36"
              strokeWidth="2"
              strokeOpacity="0.45"
            />
            {/* Branch 1 to Neural Reasoner */}
            <path d="M 0 30 L 50 30" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 2 to Autonomous Buyer */}
            <path d="M 0 90 L 50 90" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 3 to Citation Synthesizer */}
            <path d="M 0 150 L 50 150" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 4 to Semantic Discovery */}
            <path d="M 0 210 L 50 210" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />

            {/* Junction node */}
            <circle cx="50" cy="120" r="4" fill="#1f3d36" />
            <circle cx="50" cy="30" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="90" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="150" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="210" r="2.5" fill="#1f3d36" opacity="0.6" />

            {/* Animated brand green pulse travelling from left branches to center */}
            <circle r="3.5" fill="#1f3d36">
              <animateMotion
                path="M 0 90 L 50 90 L 50 120 L 100 120"
                dur="2.5s"
                repeatCount="indefinite"
              />
            </circle>
            <circle r="3.5" fill="#2f6b4f">
              <animateMotion
                path="M 0 150 L 50 150 L 50 120 L 100 120"
                dur="2.5s"
                begin="1.2s"
                repeatCount="indefinite"
              />
            </circle>
          </svg>

          {/* Label over wire */}
          <div className="absolute top-1/2 -translate-y-6 left-1/2 -translate-x-1/2 whitespace-nowrap bg-paper-100 px-1 text-[8px] font-mono text-ink-500 uppercase tracking-widest border border-line">
            EVERY ACTION
          </div>
        </div>

        {/* ================= ZONE 2: CENTER (DRISTIK AI CONTROL PLANE) ================= */}
        <div className="lg:col-span-3">
          <div
            onClick={() => setSelectedNode('control_plane')}
            className={`cursor-pointer rounded-xl border p-4 transition-all duration-300 relative ${
              selectedNode === 'control_plane'
                ? 'bg-paper-50 border-pine shadow-md ring-1 ring-pine/30'
                : 'bg-paper-50 border-line hover:border-pine hover:bg-pine-100/40'
            }`}
          >
            {/* Header with Title & Dual indicator lights */}
            <div className="flex items-start justify-between pb-3 border-b border-line">
              <div>
                <span className="text-[9px] font-mono text-ink-400 uppercase tracking-wider block">
                  DRISTIK ENGINE
                </span>
                <h4 className="text-base font-bold text-ink tracking-wider">
                  AI CONTROL PLANE
                </h4>
              </div>
              {/* Dual indicator lights (Blue + Red as in reference) */}
              <div className="flex items-center gap-1.5 pt-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-sky-500 shadow-[0_0_4px_rgba(14,165,233,0.5)]" />
                <span className="w-2.5 h-2.5 rounded-sm bg-bad shadow-[0_0_4px_rgba(154,59,50,0.5)]" />
              </div>
            </div>

            {/* Sub-tabs: IDENTITY | POLICY */}
            <div className="grid grid-cols-2 gap-1 py-2 text-[10px] font-mono border-b border-line">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setActiveTab('IDENTITY'); }}
                className={`py-1 text-center rounded transition-colors ${
                  activeTab === 'IDENTITY' ? 'bg-sky-100 text-sky-900 font-bold border border-sky-300' : 'text-ink-500 hover:text-ink'
                }`}
              >
                ■ IDENTITY
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setActiveTab('POLICY'); }}
                className={`py-1 text-center rounded transition-colors ${
                  activeTab === 'POLICY' ? 'bg-rose-100 text-rose-900 font-bold border border-rose-300' : 'text-ink-500 hover:text-ink'
                }`}
              >
                ■ POLICY
              </button>
            </div>

            {/* Alert Banner (Matching BLOCKED PII EXPOSURE style in reference) */}
            <div className="my-2.5 px-2.5 py-1.5 rounded bg-rose-50 border border-rose-200 text-bad text-center font-mono text-[10px] tracking-wider font-semibold">
              BLOCKED · PII & PRICING EXPOSURE
            </div>

            {/* AUDIT LOG Terminal Stream */}
            <div className="bg-paper-100 border border-line rounded-lg p-2.5 font-mono text-[10px] space-y-1.5 mt-2">
              <div className="text-[9px] uppercase tracking-wider text-ink-400 pb-1 border-b border-line flex items-center justify-between">
                <span>AUDIT LOG</span>
                <span className="text-good text-[9px] flex items-center gap-1 font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-good animate-ping" />
                  LIVE
                </span>
              </div>

              {AUDIT_STREAM_EVENTS.map((ev, i) => {
                const isCurrent = i === streamIndex;
                return (
                  <div
                    key={i}
                    className={`flex items-center gap-1.5 transition-all duration-300 ${
                      isCurrent
                        ? 'opacity-100 font-semibold text-ink bg-paper-50 px-1 rounded shadow-2xs'
                        : 'opacity-50 text-ink-500'
                    }`}
                  >
                    <span className={ev.status === 'allow' ? 'text-good font-bold' : ev.status === 'patch' ? 'text-pine font-bold' : 'text-bad font-bold'}>
                      {ev.status === 'allow' ? '■ allow' : ev.status === 'patch' ? '⚡ patch' : '× block'}
                    </span>
                    <span className="truncate">
                      {ev.action}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="mt-2 text-center text-[9px] font-mono text-ink-400">
              Zero hallucination · 100% DOM verified
            </div>
          </div>
        </div>

        {/* ================= SVG BRANCH CONNECTOR: CENTER -> RIGHT ================= */}
        <div className="hidden lg:flex lg:col-span-1 h-72 items-center justify-center relative">
          <svg className="w-full h-full" viewBox="0 0 100 240" fill="none" preserveAspectRatio="none">
            {/* Trunk line from center to right convergence */}
            <path
              d="M 0 120 L 50 120"
              stroke="#1f3d36"
              strokeWidth="2"
              strokeOpacity="0.45"
            />
            {/* Vertical spine connecting the 4 branches */}
            <path
              d="M 50 30 L 50 210"
              stroke="#1f3d36"
              strokeWidth="2"
              strokeOpacity="0.45"
            />
            {/* Branch 1 to Code Pack */}
            <path d="M 50 30 L 100 30" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 2 to 3 Scores */}
            <path d="M 50 90 L 100 90" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 3 to Competitor Battlecard */}
            <path d="M 50 150 L 100 150" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />
            {/* Branch 4 to Before/After Proof */}
            <path d="M 50 210 L 100 210" stroke="#1f3d36" strokeWidth="2" strokeOpacity="0.45" />

            {/* Junction node */}
            <circle cx="50" cy="120" r="4" fill="#1f3d36" />
            <circle cx="50" cy="30" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="90" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="150" r="2.5" fill="#1f3d36" opacity="0.6" />
            <circle cx="50" cy="210" r="2.5" fill="#1f3d36" opacity="0.6" />

            {/* Animated brand green pulses travelling from center to right deliverables */}
            <circle r="3.5" fill="#1f3d36">
              <animateMotion
                path="M 0 120 L 50 120 L 50 30 L 100 30"
                dur="2.5s"
                repeatCount="indefinite"
              />
            </circle>
            <circle r="3.5" fill="#2f6b4f">
              <animateMotion
                path="M 0 120 L 50 120 L 50 150 L 100 150"
                dur="2.5s"
                begin="1.2s"
                repeatCount="indefinite"
              />
            </circle>
          </svg>

          {/* Label over wire */}
          <div className="absolute top-1/2 -translate-y-6 left-1/2 -translate-x-1/2 whitespace-nowrap bg-paper-100 px-1 text-[8px] font-mono text-ink-500 uppercase tracking-widest border border-line">
            ALLOWED ONLY
          </div>
        </div>

        {/* ================= ZONE 3: RIGHT (YOUR SYSTEMS / GOVERNED) ================= */}
        <div className="lg:col-span-3">
          <div className="border border-line rounded-xl p-3.5 bg-paper-50 relative shadow-2xs">
            {/* Box Header */}
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <span className="font-mono text-[10px] text-ink-500 uppercase tracking-widest font-semibold">
                YOUR SYSTEMS · GOVERNED
              </span>
              <span className="text-[9px] font-mono text-good bg-good/10 px-2 py-0.5 rounded border border-good/20 font-semibold">
                PROVEN
              </span>
            </div>

            {/* 4 Governed Output Cards */}
            <div className="space-y-2.5 mt-3">
              {/* Ready Code Pack */}
              <button
                type="button"
                onClick={() => setSelectedNode('codepack')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'codepack'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                      GOVERNED
                    </div>
                    <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-sm bg-sky-600" />
                      1-CLICK CODE PACK
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-pine bg-pine/10 px-1.5 py-0.5 rounded border border-pine/20 font-medium">
                    ZIP Ready
                  </span>
                </div>
              </button>

              {/* 3 Honest Scores */}
              <button
                type="button"
                onClick={() => setSelectedNode('scores')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'scores'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                      GOVERNED
                    </div>
                    <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-sm bg-good" />
                      THE 3 HONEST SCORES
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-ink-500 bg-paper-200 px-1.5 py-0.5 rounded">
                    0–100
                  </span>
                </div>
              </button>

              {/* Competitor Battlecard */}
              <button
                type="button"
                onClick={() => setSelectedNode('battlecard')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'battlecard'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                      GOVERNED
                    </div>
                    <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-sm bg-warn" />
                      1-COMPETITOR BATTLECARD
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-warn bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 font-medium">
                    Bake-off
                  </span>
                </div>
              </button>

              {/* Before -> After Proof */}
              <button
                type="button"
                onClick={() => setSelectedNode('requery')}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 relative group ${
                  selectedNode === 'requery'
                    ? 'bg-pine-100 border-pine shadow-sm ring-1 ring-pine/30'
                    : 'bg-paper-100 border-line hover:border-pine hover:bg-pine-100/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">
                      GOVERNED
                    </div>
                    <div className="text-xs font-bold text-ink tracking-wide group-hover:text-pine transition-colors flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-sm bg-purple-700" />
                      BEFORE → AFTER PROOF
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-purple-800 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 font-medium">
                    VERIFIED DELTA
                  </span>

                </div>
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* ================= BOTTOM INSPECTOR PANEL (PLAIN ENGLISH) ================= */}
      <div className="relative z-10 mt-7 p-4 sm:p-5 rounded-xl bg-paper-50 border border-line shadow-2xs">
        <div className="flex items-center justify-between gap-3 mb-2 pb-2 border-b border-line">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-pine/10 border border-pine/20 text-pine font-mono text-[10px] uppercase font-bold">
              {currentNode.category}
            </span>
            <h4 className="text-base font-bold text-ink">
              {currentNode.title}
            </h4>
          </div>
          <span className="text-[11px] text-ink-500 font-mono">
            Plain English Explanation
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs mt-3">
          <div className="p-3 rounded-lg bg-paper-100 border border-line">
            <span className="text-[10px] font-mono text-ink-500 uppercase tracking-wider block mb-1">
              What it means in simple terms:
            </span>
            <p className="text-ink-700 leading-relaxed">
              {currentNode.simpleExplanation}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-paper-100 border border-line">
            <span className="text-[10px] font-mono text-bad uppercase tracking-wider block mb-1">
              Why this hurts non-optimized sites:
            </span>
            <p className="text-ink-700 leading-relaxed">
              {currentNode.whyItMatters}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-paper-100 border border-line">
            <span className="text-[10px] font-mono text-good uppercase tracking-wider block mb-1">
              What Dristik does for you:
            </span>
            <p className="text-ink-700 leading-relaxed">
              {currentNode.dristikAction}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
