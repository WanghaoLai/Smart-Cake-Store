<template>
  <section class="info-block card reviews-block">
    <div class="block-head">
      <h3 class="block-title">
        <el-icon><ChatLineSquare /></el-icon>商品评价
        <span class="reviews-count" v-if="reviews.length">({{ reviews.length }})</span>
      </h3>
      <div class="reviews-summary" v-if="reviews.length">
        <el-rate :model-value="averageRating" disabled size="small" />
        <span class="avg-num">{{ averageRating.toFixed(1) }}</span>
      </div>
    </div>
    <div v-if="!reviews.length" class="reviews-empty">
      <el-icon :size="40"><ChatLineSquare /></el-icon>
      <p>暂无评价，期待您的第一份反馈</p>
    </div>
    <div v-else class="review-list">
      <div v-for="review in reviews" :key="review.id" class="review-item">
        <el-avatar :size="40" :src="$fileUrl(review.userAvatar) || fallbackAvatar" />
        <div class="review-main">
          <div class="review-head">
            <span class="review-user">{{ review.userName || '匿名用户' }}</span>
            <el-rate :model-value="review.rating" disabled size="small" />
            <span class="review-time">{{ review.time || '' }}</span>
          </div>
          <div class="review-content" v-if="review.content">{{ review.content }}</div>
          <div class="review-images" v-if="review.images?.length">
            <el-image v-for="(image, index) in review.images" :key="index"
              :src="$fileUrl(image)" :preview-src-list="review.images" :initial-index="index"
              preview-teleported class="review-img" fit="cover" />
          </div>
          <div class="review-reply" v-if="review.reply">
            <div class="reply-tag"><el-icon><Service /></el-icon>商家回复</div>
            <div class="reply-text">{{ review.reply }}</div>
            <div class="reply-time" v-if="review.replyTime || review.reply_time">
              {{ review.replyTime || review.reply_time }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { ChatLineSquare, Service } from '@element-plus/icons-vue'

const props = defineProps({ reviews: { type: Array, default: () => [] } })
const averageRating = computed(() => props.reviews.length
  ? props.reviews.reduce((sum, review) => sum + (review.rating || 0), 0) / props.reviews.length
  : 0)
const fallbackAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
</script>

<style scoped>
.reviews-block { padding: 20px 24px; }
.block-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.block-title { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 16px; }
.reviews-count { margin-left: 4px; color: var(--c-text-secondary); font-weight: 500; font-size: 13px; }
.reviews-summary { display: inline-flex; align-items: center; gap: 6px; }
.avg-num { font-size: 14px; font-weight: 700; color: var(--c-warning); }
.reviews-empty { padding: 36px 0; display: flex; flex-direction: column; align-items: center; gap: 8px; color: var(--c-text-placeholder); }
.reviews-empty p { margin: 0; font-size: 13px; }
.review-list { display: flex; flex-direction: column; gap: 18px; }
.review-item { display: flex; gap: 12px; padding: 14px 0; border-bottom: 1px dashed var(--c-border-light); }
.review-item:last-child { border-bottom: none; padding-bottom: 0; }
.review-main { flex: 1; min-width: 0; }
.review-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.review-user { font-size: 13px; font-weight: 600; color: var(--c-text-primary); }
.review-time { font-size: 12px; color: var(--c-text-secondary); margin-left: auto; }
.review-content { font-size: 14px; color: var(--c-text-regular); line-height: 1.7; margin: 8px 0; white-space: pre-wrap; word-break: break-word; }
.review-images { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.review-img { width: 80px; height: 80px; border-radius: 8px; cursor: pointer; background: var(--c-bg-soft); }
.review-reply { margin-top: 10px; padding: 10px 14px; background: var(--c-bg-soft); border-left: 3px solid var(--c-primary); border-radius: 6px; }
.reply-tag { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; color: var(--c-primary); }
.reply-text { font-size: 13px; color: var(--c-text-regular); line-height: 1.6; margin-top: 4px; white-space: pre-wrap; word-break: break-word; }
.reply-time { font-size: 11px; color: var(--c-text-placeholder); margin-top: 4px; }
</style>
