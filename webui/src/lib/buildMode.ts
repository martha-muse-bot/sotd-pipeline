/**
 * Build-mode flag. The public analytics build (vite.config.public.ts) defines
 * __PUBLIC_BUILD__ = true via Vite `define`; the admin build and jest do not.
 * Uses typeof so an undefined identifier evaluates to false instead of throwing.
 */
declare const __PUBLIC_BUILD__: boolean | undefined;

export const isPublicBuild = (): boolean => {
  return typeof __PUBLIC_BUILD__ !== 'undefined' && __PUBLIC_BUILD__ === true;
};
