import { useEffect, useState, type DependencyList } from "react";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: DependencyList = []
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));
    loader()
      .then((data) => {
        if (!cancelled) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setState({ data: null, loading: false, error: error.message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, deps);

  return state;
}
