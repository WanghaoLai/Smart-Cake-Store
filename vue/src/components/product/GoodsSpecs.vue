<template>
  <dl class="spec-table">
    <div class="spec-row-item">
      <dt>规格</dt>
      <dd>{{ goods.specs || '—' }}</dd>
    </div>
    <div class="spec-row-item">
      <dt>净含量</dt>
      <dd>{{ goods.weight || '—' }}</dd>
    </div>
    <div class="spec-row-item">
      <dt>适用人数</dt>
      <dd>{{ goods.serves || '—' }}</dd>
    </div>
    <div class="spec-row-item">
      <dt>保质期</dt>
      <dd>{{ goods.shelf_life || '—' }}</dd>
    </div>
    <div class="spec-row-item">
      <dt>产地</dt>
      <dd>{{ goods.origin || '—' }}</dd>
    </div>
    <div class="spec-row-item">
      <dt>分类</dt>
      <dd>{{ goods.categoryName || '—' }}</dd>
    </div>
  </dl>
</template>

<script setup>
defineProps({ goods: { type: Object, default: () => ({}) } })
</script>

<style scoped>
.spec-table {
  margin: 0;
  display: flex;
  flex-direction: column;
}

.spec-row-item {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px dashed var(--c-border-light);
  font-size: 13px;
}

.spec-row-item:last-child { border-bottom: none; }

.spec-row-item dt {
  width: 90px;
  color: var(--c-text-secondary);
  font-weight: 500;
  margin: 0;
}

.spec-row-item dd {
  flex: 1;
  color: var(--c-text-primary);
  margin: 0;
  line-height: 1.6;
}
</style>
