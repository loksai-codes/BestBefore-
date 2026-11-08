import { VerifyRequest, VerifyResponse, ClaimResult, Evidence } from '../types/api';

export interface SampleAnswer {
  id: string;
  title: string;
  category: string;
  answer: string;
}

export const SAMPLE_ANSWERS: SampleAnswer[] = [
  {
    id: 'api-pricing',
    title: 'LLM API Pricing (OpenAI & Anthropic)',
    category: 'API Pricing',
    answer:
      'OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens and $60.00 per million completion tokens. In comparison, Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens. Furthermore, GPT-3.5-Turbo remains the most cost-effective OpenAI model for lightweight tasks at $0.50 per million input tokens.',
  },
  {
    id: 'sdk-version',
    title: 'Next.js & Frontend Framework SDK',
    category: 'SDK & Tech Stack',
    answer:
      'Next.js 13 requires Node.js 16.14 or later and uses the Pages router as the default application directory. You configure data fetching through getServerSideProps. Currently, Next.js 14 is the latest stable release featuring experimental Server Actions.',
  },
  {
    id: 'leadership',
    title: 'Tech Executive Leadership',
    category: 'Leadership & Executives',
    answer:
      'Parag Agrawal serves as the Chief Executive Officer of Twitter. In corporate retail, Laxman Narasimhan leads Starbucks as its active CEO. Concurrently, Satya Nadella continues as CEO and Chairman of Microsoft.',
  },
  {
    id: 'regulation',
    title: 'AI Act & Non-Compete Regulation',
    category: 'Legal & Regulation',
    answer:
      'The FTC nationwide ban on non-compete agreements took effect on September 4, 2024, rendering existing non-competes void across the country. Under the EU AI Act, general-purpose AI model obligations will apply starting August 2025, while prohibited AI practices are banned as of early 2025.',
  },
];

function findSpan(fullText: string, sub: string) {
  const index = fullText.indexOf(sub);
  if (index === -1) {
    return { span_start: 0, span_end: sub.length };
  }
  return { span_start: index, span_end: index + sub.length };
}

export function getMockVerifyResponse(request: VerifyRequest): VerifyResponse {
  const text = request.answer.trim();

  // If text matches or resembles one of the samples, return tailored verification:
  if (text.includes('GPT-4 pricing') || text.includes('OpenAI')) {
    return createPricingSampleResponse(request.answer, request.options?.rewrite ?? true);
  } else if (text.includes('Next.js') || text.includes('Node.js')) {
    return createSdkSampleResponse(request.answer, request.options?.rewrite ?? true);
  } else if (text.includes('Parag Agrawal') || text.includes('Starbucks') || text.includes('CEO')) {
    return createLeadershipSampleResponse(request.answer, request.options?.rewrite ?? true);
  } else if (text.includes('FTC') || text.includes('EU AI Act') || text.includes('regulation')) {
    return createRegulationSampleResponse(request.answer, request.options?.rewrite ?? true);
  }

  // Fallback dynamic response for any user-entered text
  return createGenericResponse(request.answer, request.options?.rewrite ?? true);
}

function createPricingSampleResponse(answer: string, rewrite: boolean): VerifyResponse {
  const c1Text = 'GPT-4 pricing starts at $30.00 per million prompt tokens and $60.00 per million completion tokens';
  const c2Text = 'Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens';
  const c3Text = 'GPT-3.5-Turbo remains the most cost-effective OpenAI model for lightweight tasks at $0.50 per million input tokens';

  const span1 = findSpan(answer, c1Text);
  const span2 = findSpan(answer, c2Text);
  const span3 = findSpan(answer, c3Text);

  const results: ClaimResult[] = [
    {
      claim: {
        id: 'claim-price-1',
        text: c1Text,
        span_start: span1.span_start,
        span_end: span1.span_end,
        entity: 'OpenAI GPT-4',
        attribute: 'API Pricing',
        claimed_value: '$30.00 input / $60.00 output per 1M tokens',
        claim_type: 'pricing',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 18,
      current_value: 'GPT-4o at $2.50 input / $10.00 output; GPT-4 Turbo at $10.00 / $30.00',
      explanation:
        'OpenAI significantly reduced flagship model pricing with GPT-4 Turbo and GPT-4o, making the original $30/$60 GPT-4 base pricing completely obsolete.',
      evidence: [
        {
          url: 'https://openai.com/api/pricing/',
          title: 'OpenAI API Pricing & Models',
          domain: 'openai.com',
          snippet: 'GPT-4o is our flagship multimodal model, priced at $2.50 per 1M input tokens and $10.00 per 1M output tokens.',
          published_date: '2024-10-01',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
        {
          url: 'https://techcrunch.com/2024/05/13/openai-launches-gpt-4o-its-new-flagship-ai-model/',
          title: 'OpenAI launches GPT-4o with 50% price cut compared to GPT-4 Turbo',
          domain: 'techcrunch.com',
          snippet: 'GPT-4o operates at twice the speed of GPT-4 Turbo at half the cost.',
          published_date: '2024-05-13',
          authority: 'reputable',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.98,
        evidence_recency: 0.95,
        source_agreement: 0.96,
        verdict_confidence: 0.97,
        conflict_penalty: 0.05,
      },
      history: [
        { value: '$30.00 / $60.00 (GPT-4 8k release)', valid_from: '2023-03-14', verified_at: '2023-03-15T00:00:00Z' },
        { value: '$10.00 / $30.00 (GPT-4 Turbo devday)', valid_from: '2023-11-06', verified_at: '2023-11-07T00:00:00Z' },
        { value: '$2.50 / $10.00 (GPT-4o launch)', valid_from: '2024-05-13', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-price-2',
        text: c2Text,
        span_start: span2.span_start,
        span_end: span2.span_end,
        entity: 'Anthropic Claude 3 Opus',
        attribute: 'API Pricing',
        claimed_value: '$15.00 input / $75.00 output per 1M tokens',
        claim_type: 'pricing',
        volatility: 'medium',
        is_time_sensitive: true,
      },
      verdict: 'current',
      freshness_score: 96,
      current_value: '$15.00 input / $75.00 output per 1M tokens',
      explanation:
        'Anthropic maintains standard Claude 3 Opus API pricing at $15.00 per 1M prompt tokens and $75.00 per 1M completion tokens as confirmed by current official docs.',
      evidence: [
        {
          url: 'https://docs.anthropic.com/en/docs/about-claude/models',
          title: 'Claude Models Overview & Pricing Specifications',
          domain: 'anthropic.com',
          snippet: 'Claude 3 Opus rate: $15.00 per million input tokens, $75.00 per million output tokens.',
          published_date: '2024-09-15',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.92,
        source_agreement: 0.98,
        verdict_confidence: 0.96,
        conflict_penalty: 0.0,
      },
      history: [
        { value: '$15.00 / $75.00 (Claude 3 family release)', valid_from: '2024-03-04', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-price-3',
        text: c3Text,
        span_start: span3.span_start,
        span_end: span3.span_end,
        entity: 'OpenAI GPT-3.5-Turbo',
        attribute: 'Cost-Effective Model Position',
        claimed_value: 'Most cost-effective model at $0.50/1M tokens',
        claim_type: 'pricing',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 12,
      current_value: 'GPT-4o-mini at $0.15 input / $0.60 output per 1M tokens',
      explanation:
        'GPT-3.5-Turbo was replaced as the budget recommendation by GPT-4o-mini, which is 60%+ cheaper ($0.15/1M input) and significantly more capable across benchmarks.',
      evidence: [
        {
          url: 'https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/',
          title: 'GPT-4o mini: Advancing cost-efficient intelligence',
          domain: 'openai.com',
          snippet: 'GPT-4o mini is priced at 15 cents per million input tokens and 60 cents per million output tokens, over an order of magnitude more affordable than previous frontier models.',
          published_date: '2024-07-18',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.97,
        evidence_recency: 0.94,
        source_agreement: 0.95,
        verdict_confidence: 0.96,
        conflict_penalty: 0.02,
      },
      history: [
        { value: 'GPT-3.5-Turbo at $0.50 / $1.50', valid_from: '2024-01-25', verified_at: '2024-02-01T00:00:00Z' },
        { value: 'GPT-4o-mini at $0.15 / $0.60', valid_from: '2024-07-18', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
  ];

  return {
    answer,
    results,
    overall_freshness: 42,
    corrected_answer: rewrite
      ? 'OpenAI GPT-4o pricing starts at $2.50 per million prompt tokens and $10.00 per million completion tokens. In comparison, Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens. Furthermore, GPT-4o-mini is now OpenAI\'s most cost-effective model at $0.15 per million input tokens ($0.60 output), superseding GPT-3.5-Turbo.'
      : null,
    gateway: {
      total_requests: 3,
      total_tokens: 1420,
      total_cost_usd: 0.00084,
      avg_latency_ms: 245.8,
      cache_hits: 1,
      fallbacks_triggered: 0,
      models_used: [
        { name: 'llama-3.3-70b-versatile', calls: 2 },
        { name: 'mixtral-8x7b-32768', calls: 1 },
      ],
    },
    graph_available: true,
    duration_ms: 712.4,
  };
}

function createSdkSampleResponse(answer: string, rewrite: boolean): VerifyResponse {
  const c1Text = 'Next.js 13 requires Node.js 16.14 or later';
  const c2Text = 'uses the Pages router as the default application directory';
  const c3Text = 'Currently, Next.js 14 is the latest stable release featuring experimental Server Actions';

  const span1 = findSpan(answer, c1Text);
  const span2 = findSpan(answer, c2Text);
  const span3 = findSpan(answer, c3Text);

  const results: ClaimResult[] = [
    {
      claim: {
        id: 'claim-sdk-1',
        text: c1Text,
        span_start: span1.span_start,
        span_end: span1.span_end,
        entity: 'Next.js Runtime Requirement',
        attribute: 'Minimum Node.js Version',
        claimed_value: 'Node.js 16.14+',
        claim_type: 'api_version',
        volatility: 'medium',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 24,
      current_value: 'Node.js 18.18.0 or later (Node 16 reached End-of-Life)',
      explanation:
        'Node.js 16 reached official end-of-life in September 2023. Modern Next.js releases (v14/v15) mandate Node.js 18.18+ as the minimum runtime requirement.',
      evidence: [
        {
          url: 'https://nextjs.org/docs/getting-started/installation',
          title: 'Next.js Installation & System Requirements',
          domain: 'nextjs.org',
          snippet: 'System Requirements: Node.js 18.18.0 or later. Node.js 16 is no longer supported.',
          published_date: '2024-10-21',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.94,
        source_agreement: 0.97,
        verdict_confidence: 0.98,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Node.js 14.x', valid_from: '2021-10-26', verified_at: '2022-01-01T00:00:00Z' },
        { value: 'Node.js 16.14+', valid_from: '2022-10-25', verified_at: '2023-01-10T00:00:00Z' },
        { value: 'Node.js 18.18.0+', valid_from: '2023-10-26', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-sdk-2',
        text: c2Text,
        span_start: span2.span_start,
        span_end: span2.span_end,
        entity: 'Next.js Architecture',
        attribute: 'Default Router Architecture',
        claimed_value: 'Pages Router is default',
        claim_type: 'api_version',
        volatility: 'medium',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 15,
      current_value: 'App Router is default (stable since Next.js 13.4)',
      explanation:
        'The App Router has been the default recommended architecture for new Next.js projects since May 2023 (v13.4). The Pages Router is legacy/maintenance mode.',
      evidence: [
        {
          url: 'https://nextjs.org/blog/next-13-4',
          title: 'Next.js 13.4 Release: App Router Production Ready',
          domain: 'nextjs.org',
          snippet: 'App Router is now GA and the default for create-next-app templates.',
          published_date: '2023-05-04',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.98,
        evidence_recency: 0.91,
        source_agreement: 0.95,
        verdict_confidence: 0.95,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Pages router', valid_from: '2016-10-25', verified_at: '2023-04-01T00:00:00Z' },
        { value: 'App router (stable default)', valid_from: '2023-05-04', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-sdk-3',
        text: c3Text,
        span_start: span3.span_start,
        span_end: span3.span_end,
        entity: 'Next.js Release Version',
        attribute: 'Latest Stable Version & Features',
        claimed_value: 'Next.js 14 with experimental Server Actions',
        claim_type: 'product_release',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'partially_outdated',
      freshness_score: 48,
      current_value: 'Next.js 15 is current stable; Server Actions became fully stable in Next.js 14',
      explanation:
        'Server Actions graduated from experimental to fully stable in Next.js 14.0.0. Furthermore, Next.js 15 has since released with React 19 support and async request APIs.',
      evidence: [
        {
          url: 'https://nextjs.org/blog/next-15',
          title: 'Next.js 15 Release Notes',
          domain: 'nextjs.org',
          snippet: 'Next.js 15 is generally available with React 19 RC support and enhanced caching defaults.',
          published_date: '2024-10-21',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.96,
        source_agreement: 0.94,
        verdict_confidence: 0.92,
        conflict_penalty: 0.1,
      },
      history: [
        { value: 'Next.js 14 (Server actions stable)', valid_from: '2023-10-26', verified_at: '2024-01-01T00:00:00Z' },
        { value: 'Next.js 15 GA', valid_from: '2024-10-21', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
  ];

  return {
    answer,
    results,
    overall_freshness: 29,
    corrected_answer: rewrite
      ? 'Next.js 15 requires Node.js 18.18.0 or later and uses the App Router as the default application directory. Data fetching is performed directly inside async React Server Components. Currently, Next.js 15 is the latest stable release featuring React 19 support and production-ready Server Actions.'
      : null,
    gateway: {
      total_requests: 3,
      total_tokens: 1190,
      total_cost_usd: 0.00062,
      avg_latency_ms: 215.3,
      cache_hits: 0,
      fallbacks_triggered: 0,
      models_used: [{ name: 'llama-3.3-70b-versatile', calls: 3 }],
    },
    graph_available: true,
    duration_ms: 648.1,
  };
}

function createLeadershipSampleResponse(answer: string, rewrite: boolean): VerifyResponse {
  const c1Text = 'Parag Agrawal serves as the Chief Executive Officer of Twitter';
  const c2Text = 'Laxman Narasimhan leads Starbucks as its active CEO';
  const c3Text = 'Satya Nadella continues as CEO and Chairman of Microsoft';

  const span1 = findSpan(answer, c1Text);
  const span2 = findSpan(answer, c2Text);
  const span3 = findSpan(answer, c3Text);

  const results: ClaimResult[] = [
    {
      claim: {
        id: 'claim-lead-1',
        text: c1Text,
        span_start: span1.span_start,
        span_end: span1.span_end,
        entity: 'Twitter / X',
        attribute: 'Chief Executive Officer',
        claimed_value: 'Parag Agrawal',
        claim_type: 'leadership',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 5,
      current_value: 'Linda Yaccarino (CEO of X Corp since June 2023)',
      explanation:
        'Parag Agrawal was terminated in October 2022 following Elon Musk\'s acquisition of Twitter. Linda Yaccarino was officially appointed CEO of X Corp in May 2023.',
      evidence: [
        {
          url: 'https://en.wikipedia.org/wiki/Linda_Yaccarino',
          title: 'Linda Yaccarino - CEO of X Corp',
          domain: 'wikipedia.org',
          snippet: 'Linda Yaccarino took over as Chief Executive Officer of X (formerly Twitter) on June 5, 2023.',
          published_date: '2024-08-10',
          authority: 'reputable',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.94,
        evidence_recency: 0.98,
        source_agreement: 0.99,
        verdict_confidence: 0.99,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Jack Dorsey', valid_from: '2015-10-05', verified_at: '2021-11-29T00:00:00Z' },
        { value: 'Parag Agrawal', valid_from: '2021-11-29', verified_at: '2022-10-27T00:00:00Z' },
        { value: 'Elon Musk (Interim)', valid_from: '2022-10-28', verified_at: '2023-05-11T00:00:00Z' },
        { value: 'Linda Yaccarino', valid_from: '2023-06-05', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-lead-2',
        text: c2Text,
        span_start: span2.span_start,
        span_end: span2.span_end,
        entity: 'Starbucks Corporation',
        attribute: 'Chief Executive Officer',
        claimed_value: 'Laxman Narasimhan',
        claim_type: 'leadership',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 8,
      current_value: 'Brian Niccol (CEO since September 9, 2024)',
      explanation:
        'Laxman Narasimhan stepped down on August 13, 2024. Brian Niccol (former CEO of Chipotle) assumed the role of Chairman and CEO of Starbucks on September 9, 2024.',
      evidence: [
        {
          url: 'https://stories.starbucks.com/press/2024/starbucks-names-brian-niccol-as-chairman-and-ceo/',
          title: 'Starbucks Names Brian Niccol as Chairman and CEO',
          domain: 'starbucks.com',
          snippet: 'Starbucks Corporation announced that Brian Niccol has been named Chairman and Chief Executive Officer, effective September 9, 2024.',
          published_date: '2024-08-13',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.99,
        source_agreement: 0.99,
        verdict_confidence: 0.99,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Howard Schultz (Interim)', valid_from: '2022-04-04', verified_at: '2023-03-23T00:00:00Z' },
        { value: 'Laxman Narasimhan', valid_from: '2023-03-23', verified_at: '2024-08-13T00:00:00Z' },
        { value: 'Brian Niccol', valid_from: '2024-09-09', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-lead-3',
        text: c3Text,
        span_start: span3.span_start,
        span_end: span3.span_end,
        entity: 'Microsoft Corporation',
        attribute: 'Chief Executive Officer',
        claimed_value: 'Satya Nadella',
        claim_type: 'leadership',
        volatility: 'low',
        is_time_sensitive: true,
      },
      verdict: 'current',
      freshness_score: 98,
      current_value: 'Satya Nadella (CEO since 2014, Chairman since 2021)',
      explanation:
        'Satya Nadella continues to serve as Chief Executive Officer and Chairman of Microsoft Corporation.',
      evidence: [
        {
          url: 'https://news.microsoft.com/exec/satya-nadella/',
          title: 'Satya Nadella - Microsoft Leadership Profile',
          domain: 'microsoft.com',
          snippet: 'Satya Nadella is Chairman and Chief Executive Officer of Microsoft.',
          published_date: '2024-09-01',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.95,
        source_agreement: 0.99,
        verdict_confidence: 0.99,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Steve Ballmer', valid_from: '2000-01-13', verified_at: '2014-02-04T00:00:00Z' },
        { value: 'Satya Nadella', valid_from: '2014-02-04', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
  ];

  return {
    answer,
    results,
    overall_freshness: 37,
    corrected_answer: rewrite
      ? 'Linda Yaccarino serves as the Chief Executive Officer of X (formerly Twitter). In corporate retail, Brian Niccol leads Starbucks as its active CEO and Chairman. Concurrently, Satya Nadella continues as CEO and Chairman of Microsoft.'
      : null,
    gateway: {
      total_requests: 3,
      total_tokens: 1350,
      total_cost_usd: 0.00078,
      avg_latency_ms: 228.6,
      cache_hits: 1,
      fallbacks_triggered: 0,
      models_used: [
        { name: 'llama-3.3-70b-versatile', calls: 2 },
        { name: 'mixtral-8x7b-32768', calls: 1 },
      ],
    },
    graph_available: true,
    duration_ms: 685.2,
  };
}

function createRegulationSampleResponse(answer: string, rewrite: boolean): VerifyResponse {
  const c1Text = 'The FTC nationwide ban on non-compete agreements took effect on September 4, 2024, rendering existing non-competes void across the country';
  const c2Text = 'Under the EU AI Act, general-purpose AI model obligations will apply starting August 2025';
  const c3Text = 'prohibited AI practices are banned as of early 2025';

  const span1 = findSpan(answer, c1Text);
  const span2 = findSpan(answer, c2Text);
  const span3 = findSpan(answer, c3Text);

  const results: ClaimResult[] = [
    {
      claim: {
        id: 'claim-reg-1',
        text: c1Text,
        span_start: span1.span_start,
        span_end: span1.span_end,
        entity: 'FTC Non-Compete Clause Rule',
        attribute: 'Legal Enforceability Status',
        claimed_value: 'Took effect Sept 4, 2024; non-competes void nationwide',
        claim_type: 'regulation',
        volatility: 'high',
        is_time_sensitive: true,
      },
      verdict: 'outdated',
      freshness_score: 10,
      current_value: 'Enjoined & Struck Down Nationwide by US Federal District Court (Ryan LLC v. FTC)',
      explanation:
        'On August 20, 2024, U.S. District Judge Ada Brown in Texas issued a final judgment striking down the FTC\'s non-compete rule nationwide, blocking it from taking effect on September 4, 2024.',
      evidence: [
        {
          url: 'https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-announces-rule-banning-noncompetes',
          title: 'FTC Non-Compete Rule Proceedings & Litigation Updates',
          domain: 'ftc.gov',
          snippet: 'Update: On August 20, 2024, the Northern District of Texas set aside the Non-Compete Rule nationwide.',
          published_date: '2024-08-21',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
        {
          url: 'https://www.reuters.com/legal/us-judge-blocks-ftc-ban-worker-noncompete-agreements-2024-08-20/',
          title: 'US judge throws out Federal Trade Commission ban on worker noncompetes',
          domain: 'reuters.com',
          snippet: 'A federal judge in Texas blocked the FTC from enforcing a new rule that would ban agreements preventing employees from working for competitors.',
          published_date: '2024-08-20',
          authority: 'reputable',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.97,
        source_agreement: 0.98,
        verdict_confidence: 0.98,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'Proposed FTC Notice of Rulemaking', valid_from: '2023-01-05', verified_at: '2023-06-01T00:00:00Z' },
        { value: 'Adopted Rule (scheduled for Sept 4)', valid_from: '2024-04-23', verified_at: '2024-05-01T00:00:00Z' },
        { value: 'Vacated nationwide by federal court order', valid_from: '2024-08-20', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-reg-2',
        text: c2Text,
        span_start: span2.span_start,
        span_end: span2.span_end,
        entity: 'EU Artificial Intelligence Act',
        attribute: 'GPAI Model Enforcement Date',
        claimed_value: 'Obligations apply August 2025',
        claim_type: 'regulation',
        volatility: 'medium',
        is_time_sensitive: true,
      },
      verdict: 'current',
      freshness_score: 95,
      current_value: 'August 2, 2025 (12 months post-entry into force)',
      explanation:
        'The EU AI Act entered into force on August 1, 2024. Chapter V obligations for general-purpose AI (GPAI) models become legally binding exactly 12 months later on August 2, 2025.',
      evidence: [
        {
          url: 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai',
          title: 'EU Artificial Intelligence Act Implementation Timeline',
          domain: 'europa.eu',
          snippet: 'Timeline: GPAI governance rules apply 12 months after entry into force (August 2025).',
          published_date: '2024-08-01',
          authority: 'official',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.99,
        evidence_recency: 0.93,
        source_agreement: 0.97,
        verdict_confidence: 0.96,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'August 2, 2025', valid_from: '2024-07-12', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
    {
      claim: {
        id: 'claim-reg-3',
        text: c3Text,
        span_start: span3.span_start,
        span_end: span3.span_end,
        entity: 'EU Artificial Intelligence Act',
        attribute: 'Prohibited Practices Effective Date',
        claimed_value: 'Banned as of early 2025',
        claim_type: 'regulation',
        volatility: 'medium',
        is_time_sensitive: true,
      },
      verdict: 'current',
      freshness_score: 92,
      current_value: 'February 2, 2025 (6 months post-entry into force)',
      explanation:
        'Prohibitions on unacceptable risk AI practices (biometric categorization, social scoring, untargeted facial scraping) apply 6 months post-entry into force on February 2, 2025.',
      evidence: [
        {
          url: 'https://artificialintelligenceact.eu/developments/timeline/',
          title: 'EU AI Act Milestones & Timeline Guide',
          domain: 'artificialintelligenceact.eu',
          snippet: 'February 2, 2025: Prohibitions on unacceptable risk systems take effect.',
          published_date: '2024-09-01',
          authority: 'reputable',
          retrieved_at: '2026-11-05T12:00:00Z',
        },
      ],
      breakdown: {
        source_authority: 0.96,
        evidence_recency: 0.91,
        source_agreement: 0.94,
        verdict_confidence: 0.93,
        conflict_penalty: 0.0,
      },
      history: [
        { value: 'February 2, 2025', valid_from: '2024-07-12', verified_at: '2026-11-05T12:00:00Z' },
      ],
    },
  ];

  return {
    answer,
    results,
    overall_freshness: 66,
    corrected_answer: rewrite
      ? 'The FTC nationwide ban on non-compete agreements was struck down nationwide by a Texas federal court on August 20, 2024, preventing it from taking effect. Under the EU AI Act, general-purpose AI model obligations will apply starting August 2, 2025, while prohibited AI practices are banned as of February 2, 2025.'
      : null,
    gateway: {
      total_requests: 3,
      total_tokens: 1560,
      total_cost_usd: 0.00092,
      avg_latency_ms: 260.4,
      cache_hits: 0,
      fallbacks_triggered: 0,
      models_used: [{ name: 'llama-3.3-70b-versatile', calls: 3 }],
    },
    graph_available: true,
    duration_ms: 780.9,
  };
}

function createGenericResponse(answer: string, rewrite: boolean): VerifyResponse {
  const sentence = answer.split(/[.!?]/).filter((s) => s.trim().length > 15)[0] || answer.slice(0, 80);
  const span = findSpan(answer, sentence.trim());

  const genericClaim: ClaimResult = {
    claim: {
      id: 'claim-custom-1',
      text: sentence.trim(),
      span_start: span.span_start,
      span_end: span.span_end,
      entity: 'Subject Entity',
      attribute: 'Extracted Assertion',
      claimed_value: sentence.trim().slice(0, 40),
      claim_type: 'other',
      volatility: 'medium',
      is_time_sensitive: true,
    },
    verdict: 'current',
    freshness_score: 88,
    current_value: sentence.trim().slice(0, 40),
    explanation: 'Verified against current web records. No conflicting recent reports detected.',
    evidence: [
      {
        url: 'https://tavily.com',
        title: 'Live Web Verification Source',
        domain: 'tavily.com',
        snippet: `Real-time search results confirmed consistency with live web data for: ${sentence.trim().slice(0, 50)}...`,
        published_date: '2024-11-01',
        authority: 'reputable',
        retrieved_at: new Date().toISOString(),
      },
    ],
    breakdown: {
      source_authority: 0.9,
      evidence_recency: 0.85,
      source_agreement: 0.92,
      verdict_confidence: 0.88,
      conflict_penalty: 0.02,
    },
    history: [
      {
        value: sentence.trim().slice(0, 40),
        valid_from: '2024-01-01',
        verified_at: new Date().toISOString(),
      },
    ],
  };

  return {
    answer,
    results: [genericClaim],
    overall_freshness: 88,
    corrected_answer: rewrite ? answer : null,
    gateway: {
      total_requests: 1,
      total_tokens: 380,
      total_cost_usd: 0.00015,
      avg_latency_ms: 195.0,
      cache_hits: 1,
      fallbacks_triggered: 0,
      models_used: [{ name: 'llama-3.3-70b-versatile', calls: 1 }],
    },
    graph_available: true,
    duration_ms: 512.0,
  };
}

