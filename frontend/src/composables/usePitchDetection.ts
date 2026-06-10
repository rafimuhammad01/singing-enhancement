import { ref, type Ref } from "vue";
import { PitchDetector } from "pitchy";
import { PitchFilter } from "@/utils/pitchFilter";

export interface PitchDetectionOptions {
  audioContextFactory?: () => AudioContext;
  getUserMediaFn?: typeof navigator.mediaDevices.getUserMedia;
  filter?: PitchFilter;
}

export interface UsePitchDetection {
  currentMidi: Ref<number | null>;
  error: Ref<string | null>;
  isActive: Ref<boolean>;
  start(targetMidiFn: () => number | null): Promise<void>;
  stop(): void;
}

export function usePitchDetection(
  opts?: PitchDetectionOptions,
): UsePitchDetection {
  const currentMidi = ref<number | null>(null);
  const error = ref<string | null>(null);
  const isActive = ref(false);

  const filter = opts?.filter ?? new PitchFilter();

  let rafId: number | null = null;
  let audioCtx: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;

  async function start(targetMidiFn: () => number | null): Promise<void> {
    if (isActive.value) return;

    const getUserMedia =
      opts?.getUserMediaFn ??
      navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

    let stream: MediaStream;
    try {
      // Disable browser processing that destroys pitch accuracy
      stream = await getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
    } catch (e) {
      const name = (e as DOMException).name;
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        error.value = "Microphone permission denied";
      } else if (name === "NotFoundError") {
        error.value = "No microphone found";
      } else {
        error.value = (e as Error).message ?? "Microphone error";
      }
      return;
    }

    mediaStream = stream;
    error.value = null;

    const factory =
      opts?.audioContextFactory ??
      (() => new AudioContext({ latencyHint: "interactive" }));
    audioCtx = factory();

    const analyser = audioCtx.createAnalyser();
    // 4096 samples ≈ 93ms window at 44.1kHz — gives the McLeod NSDF enough
    // cycles to lock onto low pitches (sub-100Hz) where 2048 was marginal.
    analyser.fftSize = 4096;
    analyser.smoothingTimeConstant = 0;

    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);
    // Intentionally not connecting analyser to destination — we don't want mic playback

    const detector = PitchDetector.forFloat32Array(analyser.fftSize);
    const buf = new Float32Array(analyser.fftSize);

    isActive.value = true;

    let frameCount = 0;

    function tick(): void {
      if (!isActive.value) return;

      analyser.getFloatTimeDomainData(buf);
      const [hz, clarity] = detector.findPitch(buf, audioCtx!.sampleRate);
      const { smoothedMidi } = filter.step(hz, clarity, targetMidiFn());
      currentMidi.value = smoothedMidi;

      if (import.meta.env.DEV && frameCount % 30 === 0) {
        console.debug("[pitch]", hz.toFixed(1), clarity.toFixed(3));
      }
      frameCount++;

      rafId = requestAnimationFrame(tick);
    }

    rafId = requestAnimationFrame(tick);
  }

  function stop(): void {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }

    if (audioCtx !== null) {
      audioCtx.close().catch(() => {});
      audioCtx = null;
    }

    if (mediaStream !== null) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
    }

    filter.reset();
    currentMidi.value = null;
    isActive.value = false;
  }

  return { currentMidi, error, isActive, start, stop };
}
