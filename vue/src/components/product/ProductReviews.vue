<template>
  <div class="reviews-section">
    <div class="reviews-summary" v-if="reviews.length">
      <el-rate :model-value="averageRating" disabled size="small" />
      <span class="avg-num">{{ averageRating.toFixed(1) }}</span>
      <span class="total-num">共 {{ total }} 条评价</span>
    </div>
    <div v-if="!reviews.length && !loading" class="reviews-empty">
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
      <div class="load-more" v-if="reviews.length < total">
        <el-button round size="small" :loading="loading" @click="load()">加载更多评价</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ChatLineSquare, Service } from '@element-plus/icons-vue'
import request from '@/utils/request'

const props = defineProps({ goodsId: { type: [Number, String], required: true } })
const emit = defineEmits(['loaded'])

const reviews = ref([])
const total = ref(0)
const pageNum = ref(1)
const loading = ref(false)
const PAGE_SIZE = 10

const averageRating = computed(() => reviews.value.length
  ? reviews.value.reduce((sum, review) => sum + (review.rating || 0), 0) / reviews.value.length
  : 0)
const fallbackAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'

const load = () => {
  if (loading.value) return
  loading.value = true
  request.get(`/reviews/goods/${props.goodsId}`, { params: { pageNum: pageNum.value, pageSize: PAGE_SIZE } })
    .then(res => {
      if (res.code === '200') {
        reviews.value.push(...(res.data?.list || []))
        total.value = res.data?.total || 0
        pageNum.value += 1
        emit('loaded', total.value)
      }
    })
    .finally(() => { loading.value = false })
}

onMounted(load)
</script>

<style scoped>
.reviews-section { padding: 4px 0; }
.reviews-summary { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.avg-num { font-size: 15px; font-weight: 700; color: var(--c-warning); }
.total-num { font-size: 12px; color: var(--c-text-secondary); margin-left: 4px; }
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
.load-more { display: flex; justify-content: center; padding: 6px 0 2px; }
</style>
