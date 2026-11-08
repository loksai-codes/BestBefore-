import { Claim, Evidence, ClaimResult } from '../types/api';

export interface BestBeforeInfo {
  bestBeforeDate: Date | null;
  dateString: string;
  isPast: boolean;
  isTimeless: boolean;
  displayText: string;
  statusNote: string | null;
}

const VOLATILITY_HALF_LIVES: Record<string, number> = {
  high: 30,
  medium: 180,
  low: 730,
};

/**
 * Computes a claim's BestBefore shelf life based on volatility half-life
 * and the published_date (or retrieved_at) of supporting evidence.
 */
export function getClaimBestBefore(
  claim: Claim,
  evidence: Evidence[] = [],
  verdict?: string
): BestBeforeInfo {
  if (verdict === 'skipped' || !claim.is_time_sensitive) {
    return {
      bestBeforeDate: null,
      dateString: 'Timeless',
      isPast: false,
      isTimeless: true,
      displayText: 'Best before: Permanent truth (Timeless)',
      statusNote: null,
    };
  }

  const halfLifeDays = VOLATILITY_HALF_LIVES[claim.volatility.toLowerCase()] ?? 180;

  // Search for most recent valid published_date or retrieved_at from evidence
  let anchorDate: Date | null = null;

  for (const ev of evidence) {
    const raw = ev.published_date || ev.retrieved_at;
    if (raw) {
      const parsed = new Date(raw);
      if (!isNaN(parsed.getTime())) {
        if (!anchorDate || parsed > anchorDate) {
          anchorDate = parsed;
        }
      }
    }
  }

  // If no date found on evidence, fall back to current date or mark unknown
  if (!anchorDate) {
    const isOutdated = verdict === 'outdated' || verdict === 'partially_outdated';
    return {
      bestBeforeDate: null,
      dateString: 'Unknown',
      isPast: isOutdated,
      isTimeless: false,
      displayText: isOutdated
        ? 'Best before: Unknown (Re-check recommended)'
        : 'Best before: Unknown date',
      statusNote: isOutdated ? 'Re-check recommended' : null,
    };
  }

  const bestBeforeTime = anchorDate.getTime() + halfLifeDays * 24 * 60 * 60 * 1000;
  const bestBeforeDate = new Date(bestBeforeTime);
  const now = new Date();

  // If verdict is already judged outdated, it is inherently past its shelf life
  const isPast = bestBeforeDate < now || verdict === 'outdated' || verdict === 'partially_outdated';

  const dateOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };
  const formatted = bestBeforeDate.toLocaleDateString('en-US', dateOptions);

  return {
    bestBeforeDate,
    dateString: formatted,
    isPast,
    isTimeless: false,
    displayText: isPast
      ? `Best before: ${formatted} (Re-check recommended)`
      : `Best before: ${formatted}`,
    statusNote: isPast ? 'Re-check recommended' : null,
  };
}

/**
 * Checks whether a claim is past its shelf life
 */
export function isPastBestBefore(result: ClaimResult): boolean {
  if (result.verdict === 'skipped') return false;
  if (result.verdict === 'outdated' || result.verdict === 'partially_outdated') return true;
  const info = getClaimBestBefore(result.claim, result.evidence, result.verdict);
  return info.isPast;
}

