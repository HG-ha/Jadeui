<template>
  <div class="app" :class="theme">
    <!-- 标题栏 -->
    <header class="titlebar">
      <span class="title">JadeUI + Vue</span>
      <div class="controls">
        <button @click="toggleTheme">{{ theme === 'dark' ? '🌙' : '☀️' }}</button>
        <button @click="windowAction('minimize')">─</button>
        <button @click="windowAction('maximize')">□</button>
        <button @click="windowAction('close')" class="close">✕</button>
      </div>
    </header>

    <!-- 导航 -->
    <nav class="nav">
      <router-link to="/">首页</router-link>
      <router-link to="/about">关于</router-link>
    </nav>

    <!-- 内容 -->
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const theme = ref('dark')

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  if (window.jade) {
    window.jade.ipcSend('router:setTheme', theme.value)
  }
}

function windowAction(action) {
  if (window.jade) {
    window.jade.ipcSend('windowAction', action)
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Segoe UI', system-ui, sans-serif;
  transition: background 0.3s, color 0.3s;
}

.app.dark {
  background: #1a1a1a;
  color: #fff;
}

.app.light {
  background: #f5f5f5;
  color: #1a1a1a;
}

.titlebar {
  height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  -webkit-app-region: drag;
  background: rgba(0, 0, 0, 0.1);
}

.title {
  font-size: 12px;
  opacity: 0.7;
}

.controls {
  display: flex;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.controls button {
  width: 36px;
  height: 32px;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  border-radius: 4px;
}

.controls button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.controls button.close:hover {
  background: #c42b1c;
  color: white;
}

.nav {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.05);
}

.nav a {
  padding: 8px 16px;
  border-radius: 6px;
  text-decoration: none;
  color: inherit;
  opacity: 0.7;
}

.nav a:hover {
  background: rgba(0, 0, 0, 0.1);
  opacity: 1;
}

.nav a.router-link-active {
  background: #0078d4;
  color: white;
  opacity: 1;
}

.main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>

