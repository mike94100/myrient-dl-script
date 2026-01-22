// Simple test to verify build system works
describe('Build System', () => {
  test('can run tests', () => {
    expect(true).toBe(true);
  });

  test('has access to DOM', () => {
    expect(document).toBeDefined();
    expect(document.body).toBeDefined();
  });

  test('can access test globals', () => {
    expect(global.fetch).toBeDefined();
    expect(global.URL).toBeDefined();
  });
});
