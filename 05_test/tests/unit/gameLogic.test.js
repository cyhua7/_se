const {
  MIN_NUMBER,
  MAX_NUMBER,
  validateGuess,
  checkGuess,
  generateSecret
} = require('../../src/utils/gameLogic');

describe('Unit Test: 猜數字遊戲邏輯', () => {
  test('猜測小於答案時應提示 higher', () => {
    expect(checkGuess(50, 30)).toEqual({
      result: 'higher',
      message: '太小了！再大一點'
    });
  });

  test('猜測大於答案時應提示 lower', () => {
    expect(checkGuess(50, 80)).toEqual({
      result: 'lower',
      message: '太大了！再小一點'
    });
  });

  test('猜中答案時應提示 correct', () => {
    expect(checkGuess(50, 50)).toEqual({
      result: 'correct',
      message: '恭喜猜中！'
    });
  });

  test('超出範圍或非整數的猜測應被拒絕', () => {
    expect(validateGuess(0)).toBe(false);
    expect(validateGuess(101)).toBe(false);
    expect(validateGuess(1.5)).toBe(false);
    expect(validateGuess(50)).toBe(true);
  });

  test('checkGuess 收到非法數字時應拋出錯誤', () => {
    expect(() => checkGuess(50, 0)).toThrow(RangeError);
    expect(() => checkGuess(200, 50)).toThrow(RangeError);
  });

  test('generateSecret 應產生範圍內的整數', () => {
    expect(generateSecret(() => 0)).toBe(MIN_NUMBER);
    expect(generateSecret(() => 0.999999)).toBe(MAX_NUMBER);
    for (let i = 0; i < 100; i += 1) {
      const secret = generateSecret();
      expect(Number.isInteger(secret)).toBe(true);
      expect(secret).toBeGreaterThanOrEqual(MIN_NUMBER);
      expect(secret).toBeLessThanOrEqual(MAX_NUMBER);
    }
  });
});
