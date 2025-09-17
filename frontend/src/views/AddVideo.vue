<template>
  <div class="add-video-container">
    <el-card style="max-width: 800px; margin: 0 auto;">
      <template #header>
        <div style="display: flex; align-items: center; gap: 10px;">
          <el-icon><VideoPlay /></el-icon>
          <span>添加学习视频</span>
        </div>
      </template>

      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef" 
        label-width="100px"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="视频链接" prop="url">
          <el-input
            v-model="form.url"
            placeholder="请输入视频链接（支持微信、抖音、B站等）"
            :prefix-icon="Link"
            clearable
            @input="detectPlatform"
          />
          <div v-if="detectedPlatform" style="margin-top: 8px;">
            <el-tag :type="platformTagType">{{ platformName }}</el-tag>
          </div>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-rate 
            v-model="form.priority" 
            :max="5" 
            show-text
            :texts="['很低', '较低', '中等', '较高', '很高']"
          />
        </el-form-item>

        <el-form-item label="分类">
          <el-select 
            v-model="form.category_ids" 
            multiple 
            placeholder="选择分类（可选）"
            style="width: 100%"
          >
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            >
              <span :style="{ color: category.color }">● {{ category.name }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="批量添加">
          <el-switch 
            v-model="batchMode"
            active-text="批量模式"
            inactive-text="单个添加"
          />
        </el-form-item>

        <el-form-item v-if="batchMode" label="批量链接">
          <el-input
            v-model="batchUrls"
            type="textarea"
            :rows="6"
            placeholder="每行一个视频链接"
          />
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="handleSubmit" 
            :loading="processing"
            :disabled="!form.url && !batchUrls"
            style="width: 100%"
          >
            <el-icon><Plus /></el-icon>
            {{ batchMode ? '批量添加视频' : '添加视频' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 处理状态显示 -->
      <div v-if="processingVideos.length > 0" style="margin-top: 20px;">
        <el-divider>处理进度</el-divider>
        <div v-for="video in processingVideos" :key="video.id" style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>{{ video.url.slice(0, 50) }}...</span>
            <el-tag :type="getStatusTagType(video.status)">{{ getStatusText(video.status) }}</el-tag>
          </div>
          <el-progress 
            :percentage="video.progress"
            :status="video.status === 'failed' ? 'exception' : 
                    video.status === 'completed' ? 'success' : 'primary'"
          />
        </div>
      </div>

      <!-- 最近添加的视频 -->
      <div v-if="recentVideos.length > 0" style="margin-top: 30px;">
        <el-divider>最近添加</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="video in recentVideos"
            :key="video.id"
            :timestamp="formatTime(video.created_at)"
            :type="video.status === 'completed' ? 'success' : 'primary'"
          >
            <el-card>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <h4 style="margin: 0 0 5px 0;">{{ video.title || '处理中...' }}</h4>
                  <el-tag size="small">{{ getPlatformName(video.platform) }}</el-tag>
                </div>
                <el-button 
                  v-if="video.status === 'completed'"
                  type="primary" 
                  size="small"
                  @click="$router.push('/videos')"
                >
                  查看详情
                </el-button>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, FormInstance } from 'element-plus'
import { VideoPlay, Link, Plus } from '@element-plus/icons-vue'
import { useVideoStore } from '../stores/video'

const videoStore = useVideoStore()

// 响应式数据
const form = reactive({
  url: '',
  priority: 3,
  category_ids: []
})

const formRef = ref<FormInstance>()
const processing = ref(false)
const batchMode = ref(false)
const batchUrls = ref('')
const detectedPlatform = ref('')
const processingVideos = ref([])
const recentVideos = ref([])
const categories = ref([])

// 表单验证规则
const rules = {
  url: [
    { required: true, message: '请输入视频链接', trigger: 'blur' },
    { pattern: /^https?:\/\/.+/, message: '请输入有效的URL', trigger: 'blur' }
  ]
}

// 计算属性
const platformName = computed(() => {
  const platforms = {
    'douyin': '抖音',
    'weixin': '微信',
    'bilibili': 'B站',
    'youtube': 'YouTube',
    'xiaohongshu': '小红书'
  }
  return platforms[detectedPlatform.value] || '未知平台'
})

const platformTagType = computed(() => {
  const types = {
    'douyin': 'danger',
    'weixin': 'success',
    'bilibili': 'primary',
    'youtube': 'warning'
  }
  return types[detectedPlatform.value] || 'info'
})

// 方法
const detectPlatform = () => {
  const url = form.url.toLowerCase()
  if (url.includes('douyin.com') || url.includes('tiktok.com')) {
    detectedPlatform.value = 'douyin'
  } else if (url.includes('weixin') || url.includes('mp.weixin.qq.com')) {
    detectedPlatform.value = 'weixin'
  } else if (url.includes('bilibili.com')) {
    detectedPlatform.value = 'bilibili'
  } else if (url.includes('youtube.com') || url.includes('youtu.be')) {
    detectedPlatform.value = 'youtube'
  } else {
    detectedPlatform.value = ''
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    processing.value = true
    
    if (batchMode.value && batchUrls.value) {
      await handleBatchSubmit()
    } else {
      await handleSingleSubmit()
    }
    
    // 重置表单
    form.url = ''
    form.category_ids = []
    batchUrls.value = ''
    formRef.value.resetFields()
    
    ElMessage.success('视频添加成功，正在后台处理中...')
    
  } catch (error: any) {
    console.error('提交失败:', error)
    const errorMsg = error.message || '添加失败，请检查网络连接'
    ElMessage.error(errorMsg)
  } finally {
    processing.value = false
  }
}

const handleSingleSubmit = async () => {
  const result = await videoStore.addVideo({
    url: form.url,
    category_ids: form.category_ids,
    priority: form.priority
  })
  
  if (result) {
    processingVideos.value.push({
      id: result.video_id,
      url: form.url,
      status: 'processing',
      progress: 0
    })
    
    // 开始监控处理进度
    monitorProgress(result.video_id)
  }
}

const handleBatchSubmit = async () => {
  const urls = batchUrls.value.split('\n').filter(url => url.trim())
  
  for (const url of urls) {
    if (url.trim()) {
      const result = await videoStore.addVideo({
        url: url.trim(),
        category_ids: form.category_ids,
        priority: form.priority
      })
      
      if (result) {
        processingVideos.value.push({
          id: result.video_id,
          url: url.trim(),
          status: 'processing',
          progress: 0
        })
        
        monitorProgress(result.video_id)
      }
    }
  }
}

const monitorProgress = async (videoId: number) => {
  // 模拟进度监控（实际应该用WebSocket或轮询API）
  const interval = setInterval(async () => {
    try {
      const video = await videoStore.getVideo(videoId)
      const processingVideo = processingVideos.value.find(v => v.id === videoId)
      
      if (processingVideo) {
        processingVideo.status = video.status
        
        if (video.status === 'completed') {
          processingVideo.progress = 100
          clearInterval(interval)
          
          // 添加到最近视频列表
          recentVideos.value.unshift(video)
          if (recentVideos.value.length > 5) {
            recentVideos.value = recentVideos.value.slice(0, 5)
          }
        } else if (video.status === 'failed') {
          processingVideo.progress = 0
          clearInterval(interval)
        } else {
          // 模拟进度更新
          processingVideo.progress = Math.min(processingVideo.progress + 10, 90)
        }
      }
    } catch (error) {
      console.error('监控进度失败:', error)
      clearInterval(interval)
    }
  }, 2000)
}

const getStatusTagType = (status: string) => {
  const types = {
    'pending': 'info',
    'downloading': 'warning',
    'processing': 'primary',
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts = {
    'pending': '等待中',
    'downloading': '下载中',
    'processing': '处理中',
    'completed': '完成',
    'failed': '失败'
  }
  return texts[status] || '未知'
}

const getPlatformName = (platform: string) => {
  const platforms = {
    'douyin': '抖音',
    'weixin': '微信',
    'bilibili': 'B站',
    'youtube': 'YouTube',
    'xiaohongshu': '小红书'
  }
  return platforms[platform] || platform
}

const formatTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 页面加载时获取分类数据
onMounted(async () => {
  try {
    categories.value = await videoStore.getCategories()
    recentVideos.value = await videoStore.getRecentVideos(5)
  } catch (error) {
    console.error('加载数据失败:', error)
  }
})
</script>

<style scoped>
.add-video-container {
  padding: 20px;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
</style>