<script setup lang="ts">
import { useRouter } from "vue-router";
import { usePlayerStore } from "@/stores/player";
import type { SearchResult } from "@/services/api";

const props = defineProps<{ result: SearchResult }>();
const router = useRouter();
const player = usePlayerStore();

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function onClick() {
  player.selectSong(props.result);
  router.push(`/preview/${props.result.video_id}`);
}
</script>

<template>
  <button
    @click="onClick"
    class="w-full flex items-center gap-4 p-3 rounded-xl bg-[#1a1822] hover:bg-[#23202c] border border-[#2a2730] hover:border-[#3a3640] transition-colors text-left"
  >
    <img
      :src="result.thumbnail_url"
      :alt="result.title"
      class="w-14 h-14 rounded-lg object-cover shrink-0"
      loading="lazy"
    />
    <div class="min-w-0 flex-1">
      <div class="text-white font-medium truncate">{{ result.title }}</div>
      <div class="text-sm text-gray-400 truncate">
        {{ result.artist }}
        <template v-if="result.album"> · {{ result.album }}</template>
      </div>
    </div>
    <div class="text-sm text-gray-500 shrink-0">
      {{ formatDuration(result.duration_sec) }}
    </div>
  </button>
</template>
