import { useEffect, useRef, useState } from 'react';
import type { TaskState } from '../types';
import { getSSEUrl } from '../api';

export function useConversionTask(taskId: string | null): TaskState | null {
  const [state, setState] = useState<TaskState | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const es = new EventSource(getSSEUrl(taskId));
    esRef.current = es;

    es.onmessage = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as any;
        if (data.error) {
          es.close();
          return;
        }
        setState(data as TaskState);
        if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
          es.close();
        }
      } catch {
        // malformed event — ignore
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [taskId]);

  return state;
}
