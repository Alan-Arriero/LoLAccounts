const test = require('node:test');
const assert = require('node:assert/strict');
const { canPlayWith, compareRankedAccounts } = require('../static/rank-compatibility.js');

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

test('Descending rank sorting orders divisions I through IV correctly', () => {
  const accounts = [
    { game_name: 'GoldIV', tier: 'GOLD', rank: 'IV', league_points: 100 },
    { game_name: 'PlatinumIV', tier: 'PLATINUM', rank: 'IV', league_points: 0 },
    { game_name: 'GoldI', tier: 'GOLD', rank: 'I', league_points: 0 },
    { game_name: 'GoldIII', tier: 'GOLD', rank: 'III', league_points: 50 },
    { game_name: 'GoldII', tier: 'GOLD', rank: 'II', league_points: 75 },
  ];

  const descending = [...accounts].sort((a, b) => compareRankedAccounts(a, b, 'desc'));
  assert.deepEqual(descending.map(account => account.game_name),
    ['PlatinumIV', 'GoldI', 'GoldII', 'GoldIII', 'GoldIV']);

  const ascending = [...accounts].sort((a, b) => compareRankedAccounts(a, b, 'asc'));
  assert.deepEqual(ascending.map(account => account.game_name),
    ['GoldIV', 'GoldIII', 'GoldII', 'GoldI', 'PlatinumIV']);
});

test('Rank sorting handles unranked and LP ranks consistently', () => {
  const accounts = [
    { game_name: 'Unranked', tier: 'UNRANKED', rank: '', league_points: 0 },
    { game_name: 'Challenger500', tier: 'CHALLENGER', league_points: 500 },
    { game_name: 'Grandmaster200', tier: 'GRANDMASTER', league_points: 200 },
    { game_name: 'Master300', tier: 'MASTER', league_points: 300 },
  ];

  const descending = [...accounts].sort((a, b) => compareRankedAccounts(a, b, 'desc'));
  assert.deepEqual(descending.map(account => account.game_name),
    ['Challenger500', 'Grandmaster200', 'Master300', 'Unranked']);

  const ascending = [...accounts].sort((a, b) => compareRankedAccounts(a, b, 'asc'));
  assert.deepEqual(ascending.map(account => account.game_name),
    ['Unranked', 'Master300', 'Grandmaster200', 'Challenger500']);
});
