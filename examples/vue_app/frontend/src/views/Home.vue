<template>
  <div>
    <h1>👋 欢迎使用 JadeUI + Vue</h1>
    <p style="margin: 16px 0; opacity: 0.7;">
      这是一个使用 Vue 3 开发的桌面应用示例。
    </p>

    <div class="card">
      <h2>用户信息</h2>
      <div v-if="user">
        <p><strong>姓名:</strong> {{ user.name }}</p>
        <p><strong>邮箱:</strong> {{ user.email }}</p>
      </div>
      <p v-else style="opacity: 0.5;">加载中...</p>
      <button @click="fetchUser" style="margin-top: 12px;">刷新</button>
    </div>

    <div class="card">
      <h2>IPC 通信</h2>
      <p style="opacity: 0.7; margin-bottom: 12px;">
        Vue 通过 jade.ipcSend 与 Python 后端通信
      </p>
      <button @click="saveData">保存数据到后端</button>
      <p v-if="saveResult" style="margin-top: 8px; color: #10b981;">
        ✓ {{ saveResult }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const user = ref(null)
const saveResult = ref('')

function fetchUser() {
  if (window.jade) {
    // 监听响应（使用 jade.on 监听后端推送的消息）
    window.jade.on('api:getUser:response', (data) => {
      // data 可能是字符串或已解析的对象
      user.value = typeof data === 'string' ? JSON.parse(data) : data
    })
    // 发送请求（使用 jade.invoke 调用后端函数）
    window.jade.invoke('api:getUser', '')
  }
}

function saveData() {
  if (window.jade) {
    window.jade.on('api:saveData:response', (data) => {
      const result = typeof data === 'string' ? JSON.parse(data) : data
      if (result.success) {
        saveResult.value = '数据已保存!'
        setTimeout(() => saveResult.value = '', 2000)
      }
    })
    window.jade.invoke('api:saveData', JSON.stringify({ test: 'data' }))
  }
}

onMounted(() => {
  fetchUser()
})
</script>

<style scoped>
.card {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.card h2 {
  margin-bottom: 12px;
  font-size: 16px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #0078d4;
  color: white;
  cursor: pointer;
  font-size: 13px;
}

button:hover {
  background: #1a86d9;
}
</style>

