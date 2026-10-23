const express = require('express');
const path = require('path');
const { MIN_NUMBER, MAX_NUMBER, validateGuess, checkGuess } = require('./utils/gameLogic');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 健康檢查 API
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// 遊戲設定 API
app.get('/api/game/config', (req, res) => {
  res.json({ min: MIN_NUMBER, max: MAX_NUMBER });
});

// 猜數字 API
app.post('/api/guess', (req, res) => {
  const { secret, guess } = req.body;

  if (!validateGuess(secret) || !validateGuess(guess)) {
    return res.status(400).json({
      error: `secret 與 guess 必須是 ${MIN_NUMBER} 到 ${MAX_NUMBER} 之間的整數`
    });
  }

  res.json(checkGuess(secret, guess));
});

// 僅在非測試環境下啟動 Port 監聽
if (process.env.NODE_ENV !== 'test') {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
}

module.exports = app;
