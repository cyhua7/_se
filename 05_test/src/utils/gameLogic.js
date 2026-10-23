const MIN_NUMBER = 1;
const MAX_NUMBER = 100;

function validateGuess(guess) {
  return Number.isInteger(guess) && guess >= MIN_NUMBER && guess <= MAX_NUMBER;
}

function checkGuess(secret, guess) {
  if (!validateGuess(secret) || !validateGuess(guess)) {
    throw new RangeError(`數字必須是 ${MIN_NUMBER} 到 ${MAX_NUMBER} 之間的整數`);
  }

  if (guess < secret) {
    return { result: 'higher', message: '太小了！再大一點' };
  }
  if (guess > secret) {
    return { result: 'lower', message: '太大了！再小一點' };
  }
  return { result: 'correct', message: '恭喜猜中！' };
}

function generateSecret(random = Math.random) {
  return Math.floor(random() * (MAX_NUMBER - MIN_NUMBER + 1)) + MIN_NUMBER;
}

module.exports = { MIN_NUMBER, MAX_NUMBER, validateGuess, checkGuess, generateSecret };
