<template>
  <div>
    <h1>关于</h1>
    <div class="card">
      <h2>技术栈</h2>
      <ul>
        <li>Vue 3 - 前端框架</li>
        <li>Vue Router - 前端路由</li>
        <li>Vite - 构建工具</li>
        <li>JadeUI - 桌面容器</li>
        <li>Python - 后端逻辑</li>
      </ul>
    </div>

    <div class="card">
      <h2>工作原理</h2>
      <ol>
        <li>Vue 应用构建为静态文件</li>
        <li>JadeUI 加载静态文件</li>
        <li>通过 jade.ipcSend/invoke 与 Python 通信</li>
      </ol>
    </div>

    <router-link to="/" class="back-btn">← 返回首页</router-link>
  </div>
</template>

<style scoped>
.card {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  padding: 20px;
  margin: 16px 0;
}

.card h2 {
  margin-bottom: 12px;
  font-size: 16px;
}

ul, ol {
  padding-left: 24px;
  line-height: 2;
  opacity: 0.8;
}

.back-btn {
  display: inline-block;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  text-decoration: none;
  color: inherit;
}

.back-btn:hover {
  background: rgba(0, 0, 0, 0.2);
}
</style>

