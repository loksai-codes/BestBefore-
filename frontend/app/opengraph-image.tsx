import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export const alt = 'BestBefore — A best-before date for every AI answer.';
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = 'image/png';

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#09090b',
          backgroundImage: 'radial-gradient(circle at 25% 25%, #18181b 0%, #09090b 100%)',
          padding: '60px 80px',
          justifyContent: 'space-between',
          fontFamily: 'sans-serif',
          color: '#f4f4f5',
        }}
      >
        {/* Top Header Bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Logo Mark + Wordmark */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '14px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '2px solid #10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#34d399',
                fontSize: '28px',
                fontWeight: 'bold',
              }}
            >
              🏷️
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', fontSize: '38px', letterSpacing: '-0.02em' }}>
              <span style={{ fontWeight: 400, color: '#e4e4e7' }}>Best</span>
              <span style={{ fontWeight: 800, color: '#ffffff' }}>Before</span>
            </div>
          </div>

          {/* Hackathon / Integration Badges */}
          <div style={{ display: 'flex', gap: '12px' }}>
            <div
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                backgroundColor: '#18181b',
                border: '1px solid #27272a',
                color: '#a1a1aa',
                fontSize: '16px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              ⚡ Powered by Tavily + Bifrost
            </div>
          </div>
        </div>

        {/* Center: Hero Tagline & Metaphor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '980px' }}>
          <h1
            style={{
              fontSize: '56px',
              fontWeight: 800,
              letterSpacing: '-0.03em',
              lineHeight: 1.15,
              color: '#ffffff',
              margin: 0,
            }}
          >
            A best-before date for every AI answer.
          </h1>
          <p
            style={{
              fontSize: '24px',
              color: '#a1a1aa',
              lineHeight: 1.4,
              margin: 0,
            }}
          >
            AI factual claims have a shelf life. We stamp each claim with a freshness score and an expiry date.
          </p>
        </div>

        {/* Bottom Card: Sample Stamped Claim Expiry Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#121215',
            border: '1px solid #27272a',
            borderRadius: '16px',
            padding: '24px 32px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '720px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span
                style={{
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                }}
              >
                STALE · EXPIRED
              </span>
              <span style={{ fontSize: '15px', color: '#71717a' }}>PRICING · GPT-4</span>
            </div>
            <div style={{ fontSize: '20px', color: '#e4e4e7', fontWeight: 500 }}>
              &ldquo;GPT-4 pricing is $30 per million prompt tokens.&rdquo;
            </div>
            <div style={{ fontSize: '14px', color: '#fb7185', fontWeight: 600 }}>
              Best before: May 13, 2024 · Re-check recommended (Superseded by GPT-4o @ $2.50/M)
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              width: '90px',
              height: '90px',
              borderRadius: '16px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '2px solid #ef4444',
            }}
          >
            <span style={{ fontSize: '32px', fontWeight: 800, color: '#f87171' }}>25%</span>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#fca5a5', letterSpacing: '0.05em' }}>
              FRESHNESS
            </span>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}

