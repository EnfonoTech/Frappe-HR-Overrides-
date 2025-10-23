<template>
  <BaseLayout :pageTitle="__('CRM')">
    <template #body>
      <div>
        <h1>Welcome to the CRM Page</h1>
        <iframe
          src="https://www.youtube.com/embed/dQw4w9WgXcQ"
          style="width: 100%; height: 80vh; border: none; margin-top: 1rem;"
        ></iframe>
      </div>
    </template>
  </BaseLayout>
</template>

<script setup>
import BaseLayout from "@/components/BaseLayout.vue"
</script>

<style scoped>
/* Optional styling tweaks */
</style>
