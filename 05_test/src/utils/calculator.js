function calculateTotal(items) {
  if (!Array.isArray(items)) return 0;
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

module.exports = { calculateTotal };