import useSWR from "swr";

export const fetcher = (url) =>
  fetch(url).then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  });

/**
 * Generic cached GET hook.
 * Returns { data, error, isLoading, isValidating, refresh }
 */
export function useCache(url) {
  const { data, error, isLoading, isValidating, mutate } = useSWR(
    url ?? null,
    fetcher,
    {
      revalidateOnFocus: false,      // Don't refetch when window regains focus
      revalidateOnReconnect: true,   // Refetch when network reconnects
      dedupingInterval: 5000,        // Deduplicate requests within 5 seconds
    }
  );

  return {
    data,
    error,
    isLoading,
    isValidating,
    refresh: () => mutate(),
    mutate,
  };
}
