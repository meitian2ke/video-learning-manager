import { createRouter, createWebHistory } from 'vue-router'
import AddVideo from '../views/AddVideo.vue'
import VideoList from '../views/VideoList.vue'

const routes = [
  {
    path: '/',
    name: 'AddVideo',
    component: AddVideo
  },
  {
    path: '/videos',
    name: 'VideoList',
    component: VideoList
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router