<script setup lang="ts">
import { computed } from "vue";
import type { JobStatusName } from "@/services/api";

const props = defineProps<{
  status: JobStatusName | "idle";
  message: string;
}>();

interface StageMeta {
  label: string;
  /** Progress percentage when this stage is active (0–100). */
  progress: number;
}

// Stage-to-progress mapping. Values reflect typical wall-clock duration weight
// of each stage on this hardware: Demucs separation dominates (~50% of total),
// CREPE melody is next, downloading + shifting are short tails.
const STAGES: Record<JobStatusName | "idle", StageMeta> = {
  idle: { label: "", progress: 0 },
  queued: { label: "Queued...", progress: 5 },
  downloading: { label: "Downloading full song...", progress: 18 },
  separating: { label: "Separating vocals from instrumental...", progress: 65 },
  melody: { label: "Extracting melody...", progress: 85 },
  shifting: { label: "Shifting to your key...", progress: 97 },
  done: { label: "Ready!", progress: 100 },
  error: { label: "", progress: 0 },
};

const meta = computed(() => STAGES[props.status] ?? STAGES.idle);
const isError = computed(() => props.status === "error");
const isDone = computed(() => props.status === "done");
const isActive = computed(
  () => props.status !== "idle" && !isError.value && !isDone.value,
);

// Time hint based on which heavy stage we're in.
const timeHint = computed(() => {
  switch (props.status) {
    case "queued":
    case "downloading":
    case "separating":
      return "This typically takes 1–3 minutes";
    case "melody":
    case "shifting":
      return "Almost done…";
    default:
      return "";
  }
});

const visible = computed(() => props.status !== "idle");
</script>

<template>
  <div
    v-if="visible"
    class="rounded-xl p-4 border"
    :class="{
      'bg-red-900/30 border-red-800': isError,
      'bg-[#1a1822] border-[#2ca02c]': isDone,
      'bg-[#1a1822] border-[#2a2730]': isActive,
    }"
  >
    <!-- Progress bar (hidden in error state) -->
    <div v-if="!isError" class="mb-3">
      <div class="h-2 rounded-full bg-[#2a2730] overflow-hidden">
        <div
          class="h-full bg-[#2ca02c] transition-all duration-700 ease-out"
          :style="{ width: `${meta.progress}%` }"
        />
      </div>
    </div>

    <!-- Label + dot + time hint -->
    <div class="flex items-start gap-3">
      <span
        v-if="isActive"
        class="inline-block w-3 h-3 rounded-full bg-[#2ca02c] animate-pulse shrink-0 mt-1.5"
      />
      <div class="flex-1 min-w-0">
        <div
          :class="{
            'text-red-200': isError,
            'text-[#2ca02c]': isDone,
            'text-gray-300': isActive,
          }"
        >
          <template v-if="isError">
            Error: {{ message || "something went wrong" }}
          </template>
          <template v-else>
            {{ meta.label }}
          </template>
        </div>
        <div v-if="timeHint" class="text-xs text-gray-500 mt-1">
          {{ timeHint }}
        </div>
      </div>
    </div>
  </div>
</template>
