import { useEffect, useRef, useState } from 'react';
import type { TaskState } from '../types';
import { getSSEUrl, getSSEBatchUrl, getTaskStatus } from '../api';

export function useConversionTask(
  taskId: string | null,
  isBatch: boolean = false
): { state: TaskState | null; isReconnecting: boolean } {
  const [state, setState] = useState<TaskState | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const timeoutRef = useRef<number | ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!taskId) {
      setState(null);
      setIsReconnecting(false);
      return;
    }

    let isMounted = true;

    const connect = async () => {
      if (retryCountRef.current > 0) {
        try {
          const currentStatus = await getTaskStatus(taskId);
          if (isMounted) {
            setState(currentStatus);
            if (currentStatus.status === 'SUCCESS' || currentStatus.status === 'FAILURE') {
              setIsReconnecting(false);
              return;
            }
          }
        } catch (e) {
          // Ignore state fetch error, proceed to reconnect
        }
      }

      if (!isMounted) return;

      const url = isBatch ? getSSEBatchUrl(taskId) : getSSEUrl(taskId);
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        if (isMounted) {
          setIsReconnecting(false);
          retryCountRef.current = 0;
        }
      };

      es.onmessage = (ev: MessageEvent<string>) => {
        try {
          const data = JSON.parse(ev.data) as any;
          if (data.error) {
            es.close();
            return;
          }
          if (isMounted) setState(data as TaskState);
          if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
            es.close();
            if (isMounted) setIsReconnecting(false);
          }
        } catch {
          // malformed event — ignore
        }
      };

      es.onerror = () => {
        es.close();
        if (isMounted) {
          setIsReconnecting(true);
          const backoff = Math.min(2 ** retryCountRef.current, 30) * 1000;
          retryCountRef.current += 1;
          timeoutRef.current = setTimeout(connect, backoff);
        }
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (esRef.current) esRef.current.close();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [taskId, isBatch]);

  return { state, isReconnecting };
}
