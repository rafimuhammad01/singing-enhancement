<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePlayerStore } from "@/stores/player";
import { transposeKey, shortKey } from "@/utils/key";
import KeySelector from "@/components/KeySelector.vue";
import AudioPlayer from "@/components/AudioPlayer.vue";

const route = useRoute();
const router = useRouter();
const player = usePlayerStore();

const SHIFT_DEBOUNCE_MS = 600;

const routeVideoId = computed(() => {
  const v = route.params.videoId;
  return Array.isArray(v) ? v[0] : v;
});

const noContext = computed(
  () => !player.videoId || player.videoId !== routeVideoId.value,
);

const shiftPending = ref(false);
// Pending semitones — updates instantly on click for snappy UI feedback.
// The actual /api/preview-shift fires only after a 600ms debounce.
const pendingSemitones = ref(player.semitones);
let shiftTimer: ReturnType<typeof setTimeout> | null = null;

// Key display reads pendingSemitones so the user sees "A → D" immediately
// even while the audio is still catching up.
const originalShort = computed(() => shortKey(player.previewKey));
const transposedShort = computed(() =>
  shortKey(transposeKey(player.previewKey, pendingSemitones.value)),
);
const showKeyLine = computed(() => player.previewKey !== "");
const keyDisplay = computed(() => {
  if (!originalShort.value) return "";
  if (pendingSemitones.value === 0) return `Key: ${originalShort.value}`;
  return `Key: ${originalShort.value} → ${transposedShort.value}`;
});

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function onSemitonesChange(n: number) {
  pendingSemitones.value = n;
  if (shiftTimer !== null) {
    clearTimeout(shiftTimer);
  }
  shiftTimer = setTimeout(async () => {
    shiftTimer = null;
    if (shiftPending.value || n === player.semitones) return;
    shiftPending.value = true;
    try {
      await player.setSemitones(n);
    } finally {
      shiftPending.value = false;
    }
  }, SHIFT_DEBOUNCE_MS);
}

async function onGenerateClick() {
  // Flush any pending debounce — user intent is clear once they hit Generate.
  if (shiftTimer !== null) {
    clearTimeout(shiftTimer);
    shiftTimer = null;
  }
  // Use the displayed pendingSemitones value so the generated key matches what
  // the user just selected, even if the preview-shift hadn't committed yet.
  player.semitones = pendingSemitones.value;

  try {
    await player.startGenerate();
    router.push(`/play/${player.videoId}/${player.semitones}`);
  } catch (e) {
    alert(`Could not start generation: ${e}`);
  }
}

onMounted(() => {
  if (!noContext.value) {
    pendingSemitones.value = player.semitones;
    player.loadPreviewKey();
  }
});

onUnmounted(() => {
  if (shiftTimer !== null) clearTimeout(shiftTimer);
});
</script>

<template>
  <div class="max-w-3xl w-full mx-auto px-4 py-8 min-h-screen">
    <button
      @click="router.push('/')"
      class="mb-6 text-sm text-gray-400 hover:text-white transition-colors"
    >
      ← Back to search
    </button>

    <div
      v-if="noContext"
      class="rounded-xl p-8 bg-[#1a1822] border border-[#2a2730] text-center"
    >
      <p class="text-white mb-4">
        Pick a song from search to load the preview.
      </p>
      <button
        @click="router.push('/')"
        class="px-6 py-3 rounded-full bg-[#2ca02c] hover:bg-[#249027] text-white transition-colors"
      >
        Go to search
      </button>
    </div>

    <template v-else>
      <!-- Song header -->
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-white mb-1">
          {{ player.song?.title }}
        </h1>
        <div class="text-gray-400">
          <span>by {{ player.song?.artist }}</span>
          <template v-if="player.song?.album">
            · {{ player.song.album }}</template
          >
          <template v-if="player.song?.duration_sec">
            · {{ fmtDuration(player.song.duration_sec) }}
          </template>
        </div>
      </div>

      <!-- Transpose pill -->
      <div class="flex items-center gap-4 mb-3">
        <KeySelector
          :semitones="pendingSemitones"
          @change="onSemitonesChange"
        />
      </div>

      <!-- Key display -->
      <div v-if="showKeyLine" class="mb-6 text-gray-300">{{ keyDisplay }}</div>
      <div v-else class="mb-6 text-gray-600 text-sm">Loading key...</div>

      <!-- Audio player (30s preview, possibly shifted) -->
      <div class="mb-6 rounded-xl p-4 bg-[#1a1822] border border-[#2a2730]">
        <AudioPlayer :src="player.audioSrc" />
      </div>

      <div class="text-xs text-gray-500 mb-4">
        This is a 30-second preview. Generate the full song to sing along.
      </div>

      <button
        @click="onGenerateClick"
        class="px-6 py-3 rounded-full bg-[#2ca02c] hover:bg-[#249027] text-white font-medium transition-colors"
      >
        Generate Full Song
      </button>
    </template>
  </div>
</template>
