<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ semitones: number; disabled?: boolean }>();
const emit = defineEmits<{ change: [value: number] }>();

const MIN = -12;
const MAX = 12;

const label = computed(() => {
  const n = props.semitones;
  if (n === 0) return "Tr. 0";
  return `Tr. ${n > 0 ? "+" : ""}${n}`;
});

const canDec = computed(() => !props.disabled && props.semitones > MIN);
const canInc = computed(() => !props.disabled && props.semitones < MAX);

function dec() {
  if (canDec.value) emit("change", props.semitones - 1);
}
function inc() {
  if (canInc.value) emit("change", props.semitones + 1);
}
</script>

<template>
  <div
    class="inline-flex items-center rounded-full bg-[#1a1822] border border-[#2a2730] overflow-hidden"
  >
    <button
      @click="dec"
      :disabled="!canDec"
      class="px-4 py-2 text-xl text-white hover:bg-[#23202c] disabled:text-gray-600 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors"
      aria-label="Transpose down one semitone"
    >
      −
    </button>
    <div
      class="px-4 py-2 text-white font-mono tabular-nums select-none min-w-[5rem] text-center"
    >
      {{ label }}
    </div>
    <button
      @click="inc"
      :disabled="!canInc"
      class="px-4 py-2 text-xl text-white hover:bg-[#23202c] disabled:text-gray-600 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-colors"
      aria-label="Transpose up one semitone"
    >
      +
    </button>
  </div>
</template>
