const { calculateTotal } = require('../../src/utils/calculator');

describe('Unit Test: calculateTotal', () => {
  test('正確計算商品總金額', () => {
    const items = [
      { price: 100, quantity: 2 },
      { price: 50, quantity: 1 }
    ];
    expect(calculateTotal(items)).toBe(250);
  });

  test('傳入空陣列應返回 0', () => {
    expect(calculateTotal([])).toBe(0);
  });
});