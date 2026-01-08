import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import About from './views/About.vue'

// 使用 Hash 路由（适合桌面应用）
const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        { path: '/', component: Home },
        { path: '/about', component: About },
    ],
})

const app = createApp(App)
app.use(router)
app.mount('#app')

// 通知 JadeUI 后端准备好了
if (window.jade) {
    window.jade.ipcSend('router:ready', '')
}

