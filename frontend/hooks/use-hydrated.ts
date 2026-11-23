"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/**
 * False on the server and during hydration, true afterwards.
 *
 * With Cache Components, page segments can hydrate after other components have already filled the
 * shared query cache. Rendering cached data during that hydration pass would not match the
 * server HTML (which always shows the loading state), so data-driven components wait for this flag.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
