import { createRouter, createWebHistory } from 'vue-router'
import AddVideo from '../views/AddVideo.vue'
import VideoList from '../views/VideoList.vue'
import LocalVideos from '../views/LocalVideos.vue'

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
  },
  {
    path: '/local-videos',
    name: 'LocalVideos',
    component: LocalVideos
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router