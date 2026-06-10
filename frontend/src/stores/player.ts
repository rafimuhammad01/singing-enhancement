import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  previewURL,
  previewShift,
  generate as apiGenerate,
  getMelody,
  getPreviewKey,
  audioURL,
  type SearchResult,
  type MelodyResponse,
  type JobStatusName,
} from "@/services/api";

type PlayerMode = "idle" | "preview" | "preview-shift" | "full";

export const usePlayerStore = defineStore("player", () => {
  // Identity / song metadata
  const videoId = ref<string>("");
  const sig = ref<string>("");
  const song = ref<SearchResult | null>(null);

  // Transpose state
  const semitones = ref(0);

  // Audio source
  const audioSrc = ref<string>("");
  const mode = ref<PlayerMode>("idle");

  // Preview key — loaded from /api/preview-key after song selection (no generate needed)
  const previewKey = ref<string>("");

  // Melody + key (populated after /api/melody fetches; key visible only after generate done)
  const melody = ref<MelodyResponse | null>(null);
  const originalKey = computed(() => melody.value?.key ?? null);
  const transposedKey = computed(() => melody.value?.transposed_key ?? null);

  // Generate job
  const jobId = ref<string | null>(null);
  const jobStatus = ref<JobStatusName | "idle">("idle");
  const jobMessage = ref<string>("");

  // Track blob URLs so we can revoke them when replaced
  let currentBlobUrl: string | null = null;
  function setAudioSrc(url: string, isBlob = false) {
    if (currentBlobUrl) {
      URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = null;
    }
    audioSrc.value = url;
    if (isBlob) currentBlobUrl = url;
  }

  /** Called from SongCard.click — initializes the player for a given song. */
  function selectSong(result: SearchResult) {
    videoId.value = result.video_id;
    sig.value = result.sig;
    song.value = result;
    semitones.value = 0;
    previewKey.value = "";
    melody.value = null;
    jobId.value = null;
    jobStatus.value = "idle";
    jobMessage.value = "";
    setAudioSrc(previewURL(result.video_id, result.sig));
    mode.value = "preview";
  }

  /**
   * Load the original key from /api/preview-key. Idempotent — skips if
   * previewKey is already loaded for the current videoId.
   */
  async function loadPreviewKey() {
    if (!videoId.value || !sig.value) return;
    if (previewKey.value !== "") return; // already loaded
    try {
      const resp = await getPreviewKey(videoId.value, sig.value);
      previewKey.value = resp.key;
    } catch {
      // Non-fatal — key display will stay blank
    }
  }

  /** Fire /api/preview-shift and swap audioSrc to the returned blob. */
  async function setSemitones(n: number) {
    if (n === semitones.value) return;
    semitones.value = n;
    if (mode.value === "full" && melody.value !== null) {
      // After generate complete: swap to the cached shifted full audio
      setAudioSrc(audioURL(videoId.value, sig.value, n));
      // Refresh melody to get transposed_key for the new offset
      melody.value = await getMelody(videoId.value, sig.value, n);
      return;
    }
    // Otherwise we're in preview mode — fetch shifted preview blob
    if (n === 0) {
      setAudioSrc(previewURL(videoId.value, sig.value));
      mode.value = "preview";
      return;
    }
    const blob = await previewShift(videoId.value, sig.value, n);
    setAudioSrc(URL.createObjectURL(blob), true);
    mode.value = "preview-shift";
  }

  /** Kick off /api/generate. Caller drives the SSE via useSSE. */
  async function startGenerate(): Promise<string> {
    const resp = await apiGenerate(videoId.value, sig.value, semitones.value);
    jobId.value = resp.job_id;
    jobStatus.value = "queued";
    jobMessage.value = "";
    return resp.job_id;
  }

  /** Called by the SSE consumer when status updates arrive. */
  function applyStatus(status: JobStatusName, message: string) {
    jobStatus.value = status;
    jobMessage.value = message;
  }

  /** Once the generate completes, load melody (for key + Group 9) and switch audioSrc. */
  async function onGenerateDone() {
    melody.value = await getMelody(videoId.value, sig.value, semitones.value);
    setAudioSrc(audioURL(videoId.value, sig.value, semitones.value));
    mode.value = "full";
  }

  return {
    videoId,
    sig,
    song,
    semitones,
    audioSrc,
    mode,
    previewKey,
    melody,
    originalKey,
    transposedKey,
    jobId,
    jobStatus,
    jobMessage,
    selectSong,
    setSemitones,
    loadPreviewKey,
    startGenerate,
    applyStatus,
    onGenerateDone,
  };
});
