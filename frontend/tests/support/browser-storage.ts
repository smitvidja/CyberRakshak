/**
 * In-memory localStorage/sessionStorage for tests that run under plain Node.
 *
 * The session helpers read `window`, `localStorage` and `sessionStorage` as globals,
 * exactly as they do in the browser, so the tests install real Storage-shaped
 * objects rather than stubbing the functions under test.
 */
export class MemoryStorage implements Storage {
  private values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.has(key) ? (this.values.get(key) as string) : null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, String(value));
  }

  keys() {
    return [...this.values.keys()];
  }
}

export function installBrowserStorage() {
  const local = new MemoryStorage();
  const session = new MemoryStorage();
  for (const [name, value] of [
    ["localStorage", local],
    ["sessionStorage", session],
    ["window", globalThis],
  ] as const) {
    Object.defineProperty(globalThis, name, {configurable: true, value, writable: true});
  }
  return {local, session};
}
