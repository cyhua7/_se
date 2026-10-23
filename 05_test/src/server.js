const express = require('express');
const path = require('path');
const { calculateTotal } = require('./utils/calculator');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 健康檢查 API
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// 結帳計算 API
app.post('/api/checkout', (req, res) => {
  const { items } = req.body;
  if (!items) {
    return res.status(400).json({ error: 'Items required' });
  }
  const total = calculateTotal(items);
  res.json({ total });
});

// 僅在非測試環境下啟動 Port 監聽
if (process.env.NODE_ENV !== 'test') {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
}

module.exports = app;