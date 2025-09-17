<template>
  <div class="local-videos-container">
    <!-- 状态面板 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-card>
          <el-statistic title="本地视频数" :value="localVideos.length">
            <template #suffix>个</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <el-statistic title="总大小" :value="totalSizeGB" :precision="2">
            <template #suffix>GB</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div style="display: flex; align-items: center; gap: 10px;">
            <span>监控状态:</span>
            <el-tag :type="scanStatus.is_watching ? 'success' : 'info'">
              {{ scanStatus.is_watching ? '监控中' : '未监控' }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作面板 -->
    <el-card style="margin-bottom: 20px;">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>本地视频管理</span>
          <div>
            <el-button 
              type="primary" 
              @click="refreshList" 
              :loading="loading"
              style="margin-right: 10px;"
            >
              <el-icon><Refresh /></el-icon>
              刷新列表
            </el-button>
            <el-button 
              type="success" 
              @click="scanVideos" 
              :loading="scanning"
            >
              <el-icon><Search /></el-icon>
              扫描新视频
            </el-button>
            <el-button 
              :type="scanStatus.is_watching ? 'warning' : 'primary'" 
              @click="toggleWatching"
              :loading="toggleLoading"
              style="margin-left: 10px;"
            >
              <el-icon><View /></el-icon>
              {{ scanStatus.is_watching ? '停止监控' : '开始监控' }}
            </el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-alert
            title="监控目录"
            :description="scanStatus.watch_directory"
            type="info"
            :closable="false"
          />
        </el-col>
        <el-col :span="12">
          <el-alert
            :title="transcriptionConfig.mode === 'openai' ? '🌐 云端转录模式' : '💻 本地转录模式'"
            :description="getTranscriptionDescription()"
            :type="transcriptionConfig.mode === 'openai' ? 'success' : 'warning'"
            :closable="false"
            show-icon
          >
            <template #action>
              <el-switch
                v-model="autoRefresh"
                :active-text="autoRefresh ? '自动刷新开启' : '自动刷新关闭'"
                size="small"
              />
            </template>
          </el-alert>
        </el-col>
      </el-row>
    </el-card>

    <!-- 视频列表 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>视频文件列表</span>
          <div style="display: flex; gap: 10px; align-items: center;">
            <el-select 
              v-model="statusFilter" 
              placeholder="筛选状态" 
              clearable 
              style="width: 120px;"
              @change="applyFilter"
            >
              <el-option label="全部" value="" />
              <el-option label="未处理" value="unprocessed" />
              <el-option label="待处理" value="pending" />
              <el-option label="处理中" value="processing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-input
              v-model="searchQuery"
              placeholder="搜索视频文件名"
              style="width: 300px;"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredVideos" 
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="name" label="文件名" min-width="250">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <el-icon style="color: #409EFF;"><VideoPlay /></el-icon>
              <div>
                <div style="font-weight: 500;">{{ row.title || row.name }}</div>
                <div style="font-size: 12px; color: #909399;">
                  {{ row.relative_path }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="processing_status" label="处理状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getProcessingTagType(row.processing_status)"
              size="small"
            >
              {{ getProcessingText(row.processing_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <div v-if="row.processing_status === 'processing'">
              <el-progress 
                v-if="row.progress !== null && row.progress > 0"
                :percentage="row.progress"
                :status="row.progress === 100 ? 'success' : ''"
                :stroke-width="6"
              />
              <div v-else style="text-align: center;">
                <el-icon class="is-loading" style="color: #409EFF; font-size: 16px;">
                  <Loading />
                </el-icon>
                <div style="font-size: 11px; color: #909399; margin-top: 2px;">
                  {{ transcriptionConfig.mode === 'openai' ? '🌐 云端转录中...' : '💻 本地转录中...' }}
                </div>
              </div>
            </div>
            <span v-else-if="row.processing_status === 'completed'" style="color: #67C23A;">
              ✓ 完成
            </span>
            <span v-else-if="row.processing_status === 'failed'" style="color: #F56C6C;">
              ✗ 失败
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>

        <el-table-column prop="extension" label="格式" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.extension.replace('.', '') }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="size_mb" label="文件大小" width="100">
          <template #default="{ row }">
            <span>{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="modified_time" label="修改时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.modified_time) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button 
                v-if="row.processing_status === 'unprocessed' || row.processing_status === 'failed'" 
                type="primary" 
                @click="processVideo(row)"
              >
                <el-icon><Tools /></el-icon>
                处理
              </el-button>
              <el-button 
                v-if="row.processing_status === 'processing'" 
                type="warning" 
                loading
                disabled
              >
                <el-icon><Tools /></el-icon>
                处理中
              </el-button>
              <el-button 
                v-if="row.processing_status === 'completed'" 
                type="success" 
                @click="viewResult(row)"
              >
                <el-icon><Document /></el-icon>
                查看结果
              </el-button>
              <el-button type="info" @click="previewVideo(row)">
                <el-icon><View /></el-icon>
                预览
              </el-button>
              <el-button type="danger" @click="deleteVideo(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 批量操作 -->
      <div v-if="selectedVideos.length > 0" style="margin-top: 15px; padding: 10px; background-color: #f5f7fa; border-radius: 4px;">
        <span>已选择 {{ selectedVideos.length }} 个视频：</span>
        <el-button type="primary" size="small" @click="batchProcess" style="margin-left: 10px;">
          批量处理
        </el-button>
        <el-button type="danger" size="small" @click="batchDelete" style="margin-left: 10px;">
          批量删除
        </el-button>
      </div>
    </el-card>

    <!-- 视频预览对话框 -->
    <el-dialog v-model="previewDialog" title="视频预览" width="70%">
      <div v-if="selectedPreviewVideo">
        <video 
          :src="`http://localhost:8000/api/local-videos/file/${selectedPreviewVideo.name}`" 
          controls 
          style="width: 100%; max-height: 400px;"
        >
          您的浏览器不支持视频预览
        </video>
        <el-descriptions :column="2" style="margin-top: 15px;">
          <el-descriptions-item label="文件名">{{ selectedPreviewVideo.name }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(selectedPreviewVideo.size) }}</el-descriptions-item>
          <el-descriptions-item label="文件格式">{{ selectedPreviewVideo.extension }}</el-descriptions-item>
          <el-descriptions-item label="修改时间">{{ formatTime(selectedPreviewVideo.modified_time) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 处理结果查看对话框 -->
    <el-dialog v-model="resultDialog" title="视频处理结果" width="80%">
      <div v-if="videoDetail">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card header="视频信息">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="标题">{{ videoDetail.video.title }}</el-descriptions-item>
                <el-descriptions-item label="状态">
                  <el-tag :type="getStatusType(videoDetail.video.status)">
                    {{ getStatusText(videoDetail.video.status) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="处理时间">{{ formatTime(videoDetail.video.updated_at) }}</el-descriptions-item>
                <el-descriptions-item label="文件大小">{{ videoDetail.video.file_size ? formatFileSize(videoDetail.video.file_size) : '未知' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card header="处理统计">
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="字幕提取">
                  <el-tag :type="videoDetail.has_transcript ? 'success' : 'danger'">
                    {{ videoDetail.has_transcript ? '成功' : '失败' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item v-if="videoDetail.transcript" label="置信度">
                  {{ (videoDetail.transcript.confidence_score * 100).toFixed(1) }}%
                </el-descriptions-item>
                <el-descriptions-item v-if="videoDetail.transcript" label="处理耗时">
                  {{ videoDetail.transcript.processing_time }}秒
                </el-descriptions-item>
                <el-descriptions-item v-if="videoDetail.transcript" label="语言">
                  {{ videoDetail.transcript.language }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>

        <div v-if="videoDetail.transcript" style="margin-top: 20px;">
          <el-card header="处理结果">
            <el-tabs>
              <el-tab-pane label="摘要" name="summary">
                <el-text size="default">{{ videoDetail.transcript.summary }}</el-text>
              </el-tab-pane>
              <el-tab-pane label="标签" name="tags">
                <div>
                  <el-tag 
                    v-for="tag in getTags(videoDetail.transcript.tags)" 
                    :key="tag" 
                    style="margin-right: 8px; margin-bottom: 8px;"
                    type="primary"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </el-tab-pane>
              <el-tab-pane label="原始字幕" name="original">
                <el-scrollbar height="300px">
                  <pre style="white-space: pre-wrap; line-height: 1.6;">{{ videoDetail.transcript.original_text }}</pre>
                </el-scrollbar>
              </el-tab-pane>
              <el-tab-pane label="清理后字幕" name="cleaned">
                <el-scrollbar height="300px">
                  <el-text>{{ videoDetail.transcript.cleaned_text }}</el-text>
                </el-scrollbar>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </div>

        <div v-else style="margin-top: 20px;">
          <el-alert
            v-if="videoDetail.video.status === 'processing'"
            title="正在处理中"
            description="视频正在进行字幕提取，请耐心等待..."
            type="info"
            show-icon
          />
          <el-alert
            v-else-if="videoDetail.video.status === 'failed'"
            title="处理失败"
            description="字幕提取过程中发生错误，请重新处理。"
            type="error"
            show-icon
          />
          <el-alert
            v-else
            title="暂无处理结果"
            description="该视频还没有字幕提取结果，请确认处理是否完成。"
            type="warning"
            show-icon
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, Search, View, VideoPlay, Tools, Delete, Document, Loading
} from '@element-plus/icons-vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 响应式数据
const localVideos = ref([])
const scanStatus = reactive({
  watch_directory: '',
  directory_exists: false,
  is_watching: false,
  processed_count: 0
})
const transcriptionConfig = reactive({
  mode: 'openai',
  openai_available: false,
  local_model_available: true,
  auto_fallback: true
})
const loading = ref(false)
const scanning = ref(false)
const toggleLoading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const selectedVideos = ref([])
const previewDialog = ref(false)
const selectedPreviewVideo = ref(null)
const resultDialog = ref(false)
const videoDetail = ref(null)
const autoRefresh = ref(true)
const refreshInterval = ref(null)

// 计算属性
const filteredVideos = computed(() => {
  let filtered = localVideos.value
  
  // 按状态筛选
  if (statusFilter.value) {
    filtered = filtered.filter(video => video.processing_status === statusFilter.value)
  }
  
  // 按名称搜索
  if (searchQuery.value) {
    filtered = filtered.filter(video => 
      video.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      video.title.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }
  
  return filtered
})

const totalSizeGB = computed(() => {
  const totalBytes = localVideos.value.reduce((sum, video) => sum + video.size, 0)
  return (totalBytes / (1024 * 1024 * 1024))
})

// 方法
const loadLocalVideos = async () => {
  loading.value = true
  try {
    const response = await api.get('/local-videos/list')
    localVideos.value = response.data.videos
  } catch (error) {
    console.error('加载本地视频失败:', error)
    ElMessage.error('加载本地视频失败')
  } finally {
    loading.value = false
  }
}

const loadScanStatus = async () => {
  try {
    const response = await api.get('/local-videos/status')
    Object.assign(scanStatus, response.data)
  } catch (error) {
    console.error('获取扫描状态失败:', error)
  }
}

const loadTranscriptionConfig = async () => {
  try {
    const response = await api.get('/system/config')
    Object.assign(transcriptionConfig, response.data)
  } catch (error) {
    console.error('获取转录配置失败:', error)
  }
}

const refreshList = async () => {
  await Promise.all([loadLocalVideos(), loadScanStatus(), loadTranscriptionConfig()])
}

const applyFilter = () => {
  // 筛选逻辑在computed属性中自动处理
}

const scanVideos = async () => {
  scanning.value = true
  try {
    const response = await api.post('/local-videos/scan')
    ElMessage.success(response.data.message)
    await loadLocalVideos()
  } catch (error) {
    console.error('扫描视频失败:', error)
    ElMessage.error('扫描视频失败')
  } finally {
    scanning.value = false
  }
}

const toggleWatching = async () => {
  toggleLoading.value = true
  try {
    if (scanStatus.is_watching) {
      await api.post('/local-videos/stop-watching')
      ElMessage.success('已停止监控')
    } else {
      await api.post('/local-videos/start-watching')
      ElMessage.success('已开始监控')
    }
    await loadScanStatus()
  } catch (error) {
    console.error('切换监控状态失败:', error)
    ElMessage.error('操作失败')
  } finally {
    toggleLoading.value = false
  }
}

const processVideo = async (video) => {
  try {
    ElMessage.info('开始处理视频，请稍候...')
    
    // 调用视频处理API
    const response = await api.post(`/local-videos/process/${encodeURIComponent(video.name)}`)
    
    // 更新本地状态
    const index = localVideos.value.findIndex(v => v.name === video.name)
    if (index !== -1) {
      localVideos.value[index].processing_status = 'processing'
      localVideos.value[index].progress = 0
    }
    
    ElMessage.success(response.data.message)
    
    // 开始监控处理进度
    monitorVideoProgress(video.name)
    
  } catch (error) {
    console.error('处理视频失败:', error)
    const errorMsg = error.response?.data?.detail || '处理视频失败'
    ElMessage.error(errorMsg)
  }
}

const monitorVideoProgress = (videoName) => {
  // 模拟进度监控
  let progress = 0
  const interval = setInterval(() => {
    progress += 10
    
    const index = localVideos.value.findIndex(v => v.name === videoName)
    if (index !== -1) {
      localVideos.value[index].progress = progress
      localVideos.value[index].estimated_time = Math.max(0, (100 - progress) * 2) // 估算剩余时间
      
      if (progress >= 100) {
        localVideos.value[index].processing_status = 'completed'
        localVideos.value[index].estimated_time = 0
        clearInterval(interval)
        ElMessage.success(`视频 ${videoName} 处理完成`)
      }
    } else {
      clearInterval(interval)
    }
  }, 2000) // 每2秒更新一次进度
}

const previewVideo = (video) => {
  selectedPreviewVideo.value = video
  previewDialog.value = true
}

const viewResult = async (video) => {
  if (!video.video_id) {
    ElMessage.warning('该视频还没有处理记录')
    return
  }
  
  try {
    loading.value = true
    const response = await api.get(`/local-videos/video-detail/${video.video_id}`)
    videoDetail.value = response.data
    resultDialog.value = true
  } catch (error) {
    console.error('获取视频详情失败:', error)
    ElMessage.error('获取视频处理结果失败')
  } finally {
    loading.value = false
  }
}

const deleteVideo = async (video) => {
  try {
    await ElMessageBox.confirm(
      `确认删除视频文件 "${video.name}" 吗？此操作不可恢复！`,
      '确认删除',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 调用本地视频删除API
    const response = await api.delete(`/local-videos/delete/${encodeURIComponent(video.name)}`)
    ElMessage.success(response.data.message)
    await loadLocalVideos()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除视频失败:', error)
      const errorMsg = error.response?.data?.detail || '删除失败'
      ElMessage.error(errorMsg)
    }
  }
}

const handleSelectionChange = (selection) => {
  selectedVideos.value = selection
}

const batchProcess = async () => {
  ElMessage.info(`开始批量处理 ${selectedVideos.value.length} 个视频`)
  // TODO: 实现批量处理
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedVideos.value.length} 个视频文件吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // TODO: 实现批量删除
    ElMessage.success('批量删除成功')
    await loadLocalVideos()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

// 工具函数
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (timestamp) => {
  if (typeof timestamp === 'string') {
    // ISO 字符串格式
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN')
  } else {
    // Unix 时间戳格式
    const date = new Date(timestamp * 1000)
    return date.toLocaleString('zh-CN')
  }
}

const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || ''
}

const getStatusText = (status) => {
  const texts = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return texts[status] || status
}

const getTags = (tagString) => {
  if (!tagString) return []
  return tagString.split(',').map(tag => tag.trim()).filter(tag => tag)
}

const getProcessingTagType = (status) => {
  const types = {
    'unprocessed': '',
    'pending': 'info',
    'processing': 'warning', 
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || ''
}

const getProcessingText = (status) => {
  const texts = {
    'unprocessed': '未处理',
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return texts[status] || '未处理'
}

const formatEstimatedTime = (seconds) => {
  if (!seconds) return ''
  if (seconds < 60) return `约${Math.ceil(seconds)}秒`
  const minutes = Math.ceil(seconds / 60)
  return `约${minutes}分钟`
}

const getTranscriptionDescription = () => {
  if (transcriptionConfig.mode === 'openai') {
    return `使用OpenAI云端API转录，低CPU占用，支持自动降级到本地模式`
  } else {
    return `使用本地Whisper模型转录，高CPU占用，无需网络连接`
  }
}

// 自动刷新功能
const startAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
  refreshInterval.value = setInterval(async () => {
    if (autoRefresh.value) {
      await refreshList()
    }
  }, 10000) // 每10秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

// 页面加载
onMounted(async () => {
  await refreshList()
  startAutoRefresh()
})

// 页面卸载时清理
onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.local-videos-container {
  padding: 20px;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
</style>