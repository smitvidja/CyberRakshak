import {useEffect, useLayoutEffect} from "react";

// useLayoutEffect commits before the browser paints, so client-only derived state (localStorage
// reads, etc.) is applied before the first paint the user actually sees - no flash of the
// wrong/default content. Plain useEffect runs after paint, which is fine for hydration-mismatch
// warnings but not for avoiding a visible flash. useLayoutEffect itself warns when it runs during
// SSR (no DOM to lay out), so this falls back to useEffect there - "isomorphic" meaning safe in
// both environments.
export const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;
