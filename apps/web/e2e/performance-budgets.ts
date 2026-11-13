// Performance budgets checked against the demonstration package (A33, docs/engineering/E2E.md).
// Bytes and request counts were identical over four runs of 9 November 2026: bytes get about
// 10 % of margin and request counts two more requests. The time is the median of three loads,
// which measured 6.1 to 6.6 s on a laptop: its budget is wide because runners vary. A change
// that really needs more raises the budget in the same pull request and says why.
export const budgets = {
  pages: {
    home: { scriptBytes: 172_000, scriptRequests: 9 },
    directory: { scriptBytes: 172_000, scriptRequests: 10 },
    project: { scriptBytes: 184_000, scriptRequests: 11 },
    market: { scriptBytes: 499_000, scriptRequests: 14 },
    sources: { scriptBytes: 173_000, scriptRequests: 10 },
    explorer: { scriptBytes: 543_000, scriptRequests: 19 },
  } as Record<string, { scriptBytes: number; scriptRequests: number }>,
  mapLoad: { bytes: 429_000, requests: 13 },
  mapSettledMs: 15_000,
};
