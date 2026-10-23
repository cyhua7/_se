const request = require('supertest');
const app = require('../../src/server');

describe('System Test: Web API', () => {
  test('GET /api/health 應返回 200 與 ok 狀態', async () => {
    const res = await request(app).get('/api/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('POST /api/checkout 應正確回應計算金額', async () => {
    const res = await request(app)
      .post('/api/checkout')
      .send({ items: [{ price: 200, quantity: 3 }] });
    
    expect(res.statusCode).toBe(200);
    expect(res.body.total).toBe(600);
  });
});