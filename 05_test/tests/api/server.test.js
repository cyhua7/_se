const request = require('supertest');
const app = require('../../src/server');

describe('System Test: 猜數字 Web API', () => {
  test('GET /api/health 應返回 200 與 ok 狀態', async () => {
    const res = await request(app).get('/api/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('GET /api/game/config 應返回數字範圍', async () => {
    const res = await request(app).get('/api/game/config');
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ min: 1, max: 100 });
  });

  test('POST /api/guess 猜中時應返回 correct', async () => {
    const res = await request(app)
      .post('/api/guess')
      .send({ secret: 42, guess: 42 });

    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ result: 'correct', message: '恭喜猜中！' });
  });

  test('POST /api/guess 猜太小時應返回 higher', async () => {
    const res = await request(app)
      .post('/api/guess')
      .send({ secret: 42, guess: 10 });

    expect(res.statusCode).toBe(200);
    expect(res.body.result).toBe('higher');
  });

  test('POST /api/guess 猜太大時應返回 lower', async () => {
    const res = await request(app)
      .post('/api/guess')
      .send({ secret: 42, guess: 90 });

    expect(res.statusCode).toBe(200);
    expect(res.body.result).toBe('lower');
  });

  test('POST /api/guess 缺少參數或超出範圍應返回 400', async () => {
    const missing = await request(app).post('/api/guess').send({ guess: 10 });
    expect(missing.statusCode).toBe(400);

    const outOfRange = await request(app)
      .post('/api/guess')
      .send({ secret: 42, guess: 101 });
    expect(outOfRange.statusCode).toBe(400);
  });
});
