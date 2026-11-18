(function (root, factory) {
  const compatibility = factory();
  if (typeof module === 'object' && module.exports) module.exports = compatibility;
  else root.RankCompatibility = compatibility;
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  const tiers = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND',
    'MASTER', 'GRANDMASTER', 'CHALLENGER'];
  const soloQueuePeers = {
    IRON: ['IRON', 'BRONZE', 'SILVER'],
    BRONZE: ['IRON', 'BRONZE', 'SILVER'],
    SILVER: ['IRON', 'BRONZE', 'SILVER', 'GOLD'],
    GOLD: ['SILVER', 'GOLD', 'PLATINUM'],
    PLATINUM: ['GOLD', 'PLATINUM', 'EMERALD'],
  };

  function canPlaySolo(account, targetTier) {
    const accountTier = tiers.includes(account.tier) ? account.tier : 'UNRANKED';
    const rank = String(account.rank || '').toUpperCase();
    if (soloQueuePeers[targetTier]) return soloQueuePeers[targetTier].includes(accountTier);
    if (targetTier === 'EMERALD') {
      return accountTier === 'PLATINUM' || accountTier === 'EMERALD' ||
        (accountTier === 'DIAMOND' && ['IV', 'III'].includes(rank));
    }
    if (targetTier === 'DIAMOND') {
      if (accountTier === 'EMERALD') return ['II', 'I'].includes(rank);
      if (accountTier === 'DIAMOND') return true;
      const lp = account.league_points;
      return accountTier === 'MASTER' && lp !== null && lp !== '' &&
        Number.isFinite(Number(lp)) && Number(lp) < 200;
    }
    if (targetTier === 'MASTER') {
      return accountTier === 'MASTER' || (accountTier === 'DIAMOND' && rank === 'I');
    }
    return false;
  }

  function canPlayFlex(account, targetTier) {
    const accountTier = tiers.includes(account.flex_tier) ? account.flex_tier : 'UNRANKED';
    const accountRank = tiers.indexOf(accountTier);
    const targetRank = tiers.indexOf(targetTier);
    return accountRank >= 0 && targetRank >= 0 &&
      ((accountRank <= 6 && targetRank <= 6) || (accountRank >= 5 && targetRank >= 5));
  }

  function canPlayWith(account, targetTier, queue) {
    if (!account || !tiers.includes(targetTier)) return false;
    if (queue === 'solo') return canPlaySolo(account, targetTier);
    if (queue === 'flex') return canPlayFlex(account, targetTier);
    return false;
  }

  return Object.freeze({ tiers: Object.freeze(tiers), canPlayWith });
});
