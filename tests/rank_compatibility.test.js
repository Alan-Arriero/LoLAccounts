const test = require('node:test');
const assert = require('node:assert/strict');
const { canPlayWith } = require('../static/rank-compatibility.js');

test('Gold Solo/Duo includes Silver, Gold, and Platinum only', () => {
  for (const tier of ['SILVER', 'GOLD', 'PLATINUM']) {
    assert.equal(canPlayWith({ tier }, 'GOLD', 'solo'), true);
  }
  for (const tier of ['IRON', 'BRONZE', 'EMERALD', 'MASTER']) {
    assert.equal(canPlayWith({ tier, league_points: 0 }, 'GOLD', 'solo'), false);
  }
});

test('Diamond Solo/Duo respects division and Master LP limits', () => {
  assert.equal(canPlayWith({ tier: 'EMERALD', rank: 'II' }, 'DIAMOND', 'solo'), true);
  assert.equal(canPlayWith({ tier: 'EMERALD', rank: 'III' }, 'DIAMOND', 'solo'), false);
  assert.equal(canPlayWith({ tier: 'MASTER', league_points: 199 }, 'DIAMOND', 'solo'), true);
  assert.equal(canPlayWith({ tier: 'MASTER', league_points: 200 }, 'DIAMOND', 'solo'), false);
  assert.equal(canPlayWith({ tier: 'DIAMOND', rank: 'I' }, 'MASTER', 'solo'), true);
  assert.equal(canPlayWith({ tier: 'GRANDMASTER' }, 'GRANDMASTER', 'solo'), false);
});

test('Flex allows Diamond and below freely and requires Emerald for Master+', () => {
  assert.equal(canPlayWith({ flex_tier: 'IRON' }, 'DIAMOND', 'flex'), true);
  assert.equal(canPlayWith({ flex_tier: 'IRON' }, 'MASTER', 'flex'), false);
  assert.equal(canPlayWith({ flex_tier: 'EMERALD' }, 'CHALLENGER', 'flex'), true);
  assert.equal(canPlayWith({ flex_tier: 'MASTER' }, 'EMERALD', 'flex'), true);
  assert.equal(canPlayWith({ flex_tier: 'UNRANKED' }, 'GOLD', 'flex'), false);
});
