<template>
	<BaseLayout :pageTitle="__('Video')">
		<template #body>
			  <div class="video-page">
				<h1>Welcome to the Video Page</h1>
				<iframe
				width="380"
				height="215"
				src="https://www.youtube.com/embed/dQw4w9WgXcQ"
				title="YouTube video"
				frameborder="0"
				allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
				allowfullscreen
				></iframe>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>

import BaseLayout from "@/components/BaseLayout.vue"

</script>
<style scoped>
.video-page {
  text-align: center;
  margin-top: 20px;
}
</style>