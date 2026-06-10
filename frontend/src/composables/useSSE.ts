import { onUnmounted, ref } from "vue";
import type { StatusEvent } from "@/services/api";

export function useSSE() {
  const status = ref<StatusEvent | null>(null);
  const error = ref<string | null>(null);
  let source: EventSource | null = null;

  function open(url: string, onMessage?: (e: StatusEvent) => void) {
    close();
    source = new EventSource(url);
    source.onmessage = (ev) => {
      try {
        const parsed: StatusEvent = JSON.parse(ev.data as string);
        status.value = parsed;
        onMessage?.(parsed);
        if (parsed.status === "done" || parsed.status === "error") {
          close();
        }
      } catch (err) {
        error.value = `parse error: ${err}`;
        close();
      }
    };
    source.onerror = () => {
      // EventSource errors on transient disconnect AND on server close.
      // If we've already seen 'done' or 'error', we already called close().
      // If not, the stream broke unexpectedly — surface it.
      if (status.value?.status !== "done" && status.value?.status !== "error") {
        error.value = "connection lost";
      }
      close();
    };
  }

  function close() {
    if (source) {
      source.close();
      source = null;
    }
  }

  onUnmounted(close);

  return { status, error, open, close };
}
