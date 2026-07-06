<script setup>
// Greyish / translucent water-droplet backdrop (an alternative to the green
// blobs). Purely decorative; sits behind the content (which is z-10).
</script>

<template>
  <div class="fixed inset-0 overflow-hidden pointer-events-none">
    <!-- soft blue-grey glows for depth (instead of green) -->
    <div class="droplet-soft w-[520px] h-[520px] bg-slate-500 -top-40 -right-32" style="animation-delay: -3s" />
    <div class="droplet-soft w-[440px] h-[440px] bg-sky-800 bottom-0 -left-32" style="animation-delay: -13s" />
    <div class="droplet-soft w-[300px] h-[300px] bg-slate-400 top-1/3 left-1/4" style="opacity: 0.14; animation-delay: -7s" />

    <!-- glassy water droplets -->
    <div class="droplet w-40 h-40 top-24 left-[10%]" />
    <div class="droplet w-24 h-24 top-[46%] right-[8%]" />
    <div class="droplet w-16 h-16 bottom-24 left-[28%]" />
    <div class="droplet w-28 h-28 top-[18%] right-[26%]" />
    <div class="droplet w-12 h-12 bottom-1/3 right-[18%]" />
    <div class="droplet w-20 h-20 top-2/3 left-[6%]" />
  </div>
</template>
