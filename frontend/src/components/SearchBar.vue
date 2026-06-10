<script setup lang="ts">
import { ref } from "vue";

const emit = defineEmits<{ submit: [query: string] }>();
const query = ref("");

function onSubmit() {
  const trimmed = query.value.trim();
  if (trimmed) emit("submit", trimmed);
}
</script>

<template>
  <form @submit.prevent="onSubmit" class="w-full">
    <input
      v-model="query"
      type="search"
      placeholder="Search for a song"
      autocomplete="off"
      class="w-full px-6 py-4 text-lg rounded-full bg-[#1a1822] border border-[#2a2730] focus:border-[#2ca02c] focus:outline-none text-white placeholder-gray-500 transition-colors"
    />
  </form>
</template>
