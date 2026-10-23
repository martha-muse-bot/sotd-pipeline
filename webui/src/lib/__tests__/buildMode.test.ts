/**
 * Build-mode flag tests. The public build (vite.config.public.ts) defines
 * __PUBLIC_BUILD__; the admin build and jest do not (setupTests sets it to
 * false explicitly so tests can flip it).
 */
import { isPublicBuild } from '../buildMode';

describe('isPublicBuild', () => {
  const original = (globalThis as any).__PUBLIC_BUILD__;

  afterEach(() => {
    (globalThis as any).__PUBLIC_BUILD__ = original;
  });

  it('returns false when the flag is false', () => {
    (globalThis as any).__PUBLIC_BUILD__ = false;
    expect(isPublicBuild()).toBe(false);
  });

  it('returns true when the flag is true', () => {
    (globalThis as any).__PUBLIC_BUILD__ = true;
    expect(isPublicBuild()).toBe(true);
  });

  it('returns false when the flag is undefined (admin/jest default)', () => {
    delete (globalThis as any).__PUBLIC_BUILD__;
    expect(isPublicBuild()).toBe(false);
  });
});
