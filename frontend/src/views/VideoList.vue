<template>
  <div class="video-list-container">
    <!-- 统计面板 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card>
          <el-statistic title="总视频数" :value="stats.total_videos">
            <template #suffix>个</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="已完成" :value="stats.completed_videos" value-style="color: #67C23A">
            <template #suffix>个</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="学习中" :value="stats.learning_videos" value-style="color: #E6A23C">
            <template #suffix>个</template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="完成率" :value="stats.completion_rate" :precision="1" value-style="color: #409EFF">
            <template #suffix>%</template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和筛选 -->
    <el-card style="margin-bottom: 20px;">
      <el-row :gutter="20" style="align-items: end;">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="搜索视频标题或内容"
            :prefix-icon="Search"
            clearable
            @input="handleSearch"
          />
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterPlatform" placeholder="平台" clearable @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="抖音" value="douyin" />
            <el-option label="微信" value="weixin" />
            <el-option label="B站" value="bilibili" />
            <el-option label="YouTube" value="youtube" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterStatus" placeholder="处理状态" clearable @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterLearning" placeholder="学习状态" clearable @change="handleFilter">
            <el-option label="全部" value="" />
            <el-option label="待学习" value="todo" />
            <el-option label="学习中" value="learning" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 视频列表表格 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>视频列表</span>
          <el-button type="primary" size="small" @click="$router.push('/')">
            <el-icon><Plus /></el-icon>
            添加视频
          </el-button>
        </div>
      </template>

      <el-table 
        :data="videos" 
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <img 
                v-if="row.thumbnail_url" 
                :src="row.thumbnail_url" 
                style="width: 40px; height: 30px; object-fit: cover; border-radius: 4px;"
              />
              <div>
                <div style="font-weight: 500;">{{ row.title || '处理中...' }}</div>
                <div style="font-size: 12px; color: #909399;">
                  {{ formatDuration(row.duration) }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag :type="getPlatformTagType(row.platform)" size="small">
              {{ getPlatformName(row.platform) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="处理状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="learning_record.learning_status" label="学习状态" width="100">
          <template #default="{ row }">
            <el-tag 
              :type="getLearningTagType(row.learning_record?.learning_status)"
              size="small"
            >
              {{ getLearningText(row.learning_record?.learning_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="learning_record.priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-rate 
              :model-value="row.learning_record?.priority || 3" 
              disabled 
              size="small"
            />
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="添加时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group size="small">
              <el-button type="primary" @click="viewDetails(row)">
                <el-icon><View /></el-icon>
              </el-button>
              <el-button type="success" @click="startLearning(row)">
                <el-icon><VideoPlay /></el-icon>
              </el-button>
              <el-button type="warning" @click="editNotes(row)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button type="danger" @click="deleteVideo(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div style="display: flex; justify-content: center; margin-top: 20px;">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailDrawer" title="视频详情" size="50%">
      <div v-if="selectedVideo">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedVideo.title }}</el-descriptions-item>
          <el-descriptions-item label="链接">
            <el-link :href="selectedVideo.url" target="_blank">{{ selectedVideo.url }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item label="时长">{{ formatDuration(selectedVideo.duration) }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ getPlatformName(selectedVideo.platform) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>字幕内容</el-divider>
        <div v-if="selectedVideo.transcript">
          <h4>摘要</h4>
          <p>{{ selectedVideo.transcript.summary }}</p>
          
          <h4>标签</h4>
          <div style="margin-bottom: 15px;">
            <el-tag 
              v-for="tag in (selectedVideo.transcript.tags || '').split(',')" 
              :key="tag"
              style="margin-right: 8px;"
            >
              {{ tag.trim() }}
            </el-tag>
          </div>
          
          <h4>完整字幕</h4>
          <el-input
            type="textarea"
            :rows="10"
            :model-value="selectedVideo.transcript.cleaned_text"
            readonly
          />
        </div>
        <div v-else>
          <el-empty description="字幕处理中或处理失败" />
        </div>
      </div>
    </el-drawer>

    <!-- 学习笔记编辑对话框 -->
    <el-dialog v-model="notesDialog" title="学习笔记" width="50%">
      <el-form :model="notesForm" label-width="100px">
        <el-form-item label="学习状态">
          <el-select v-model="notesForm.learning_status">
            <el-option label="待学习" value="todo" />
            <el-option label="学习中" value="learning" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="实践状态">
          <el-select v-model="notesForm.practice_status">
            <el-option label="未开始" value="none" />
            <el-option label="计划中" value="planning" />
            <el-option label="实施中" value="implementing" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="学习笔记">
          <el-input
            type="textarea"
            :rows="6"
            v-model="notesForm.notes"
            placeholder="记录学习心得、要点等"
          />
        </el-form-item>
        
        <el-form-item label="代码仓库">
          <el-input
            v-model="notesForm.code_repo"
            placeholder="实践代码的GitHub仓库链接"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="notesDialog = false">取消</el-button>
        <el-button type="primary" @click="saveNotes">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, View, VideoPlay, Edit, Delete } from '@element-plus/icons-vue'
import { useVideoStore } from '../stores/video'

const videoStore = useVideoStore()

// 响应式数据
const videos = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedVideos = ref([])
const stats = ref({
  total_videos: 0,
  completed_videos: 0,
  learning_videos: 0,
  todo_videos: 0,
  total_learning_time: 0,
  practiced_videos: 0,
  completion_rate: 0
})

// 筛选相关
const searchQuery = ref('')
const filterPlatform = ref('')
const filterStatus = ref('')
const filterLearning = ref('')

// 详情抽屉
const detailDrawer = ref(false)
const selectedVideo = ref(null)

// 笔记编辑对话框
const notesDialog = ref(false)
const notesForm = reactive({
  learning_status: '',
  practice_status: '',
  notes: '',
  code_repo: ''
})
const editingVideoId = ref(null)

// 方法
const loadVideos = async () => {
  loading.value = true
  try {
    const result = await videoStore.getVideos({
      page: currentPage.value,
      size: pageSize.value,
      status: filterStatus.value,
      platform: filterPlatform.value,
      learning_status: filterLearning.value
    })
    
    videos.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('加载视频失败:', error)
    ElMessage.error('加载视频失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await videoStore.getStats()
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const handleSearch = debounce(() => {
  currentPage.value = 1
  loadVideos()
}, 500)

const handleFilter = () => {
  currentPage.value = 1
  loadVideos()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  loadVideos()
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadVideos()
}

const handleSelectionChange = (selection: any[]) => {
  selectedVideos.value = selection
}

const viewDetails = (video: any) => {
  selectedVideo.value = video
  detailDrawer.value = true
}

const startLearning = async (video: any) => {
  try {
    await videoStore.updateLearningRecord(video.id, {
      learning_status: 'learning'
    })
    ElMessage.success('开始学习')
    await loadVideos()
    await loadStats()
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const editNotes = (video: any) => {
  const record = video.learning_record || {}
  notesForm.learning_status = record.learning_status || 'todo'
  notesForm.practice_status = record.practice_status || 'none'
  notesForm.notes = record.notes || ''
  notesForm.code_repo = record.code_repo || ''
  editingVideoId.value = video.id
  notesDialog.value = true
}

const saveNotes = async () => {
  try {
    await videoStore.updateLearningRecord(editingVideoId.value, notesForm)
    ElMessage.success('保存成功')
    notesDialog.value = false
    await loadVideos()
    await loadStats()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteVideo = async (video: any) => {
  try {
    await ElMessageBox.confirm(
      '删除后无法恢复，确认删除吗？',
      '确认删除',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await videoStore.deleteVideo(video.id)
    ElMessage.success('删除成功')
    await loadVideos()
    await loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const refreshData = async () => {
  await Promise.all([loadVideos(), loadStats()])
}

// 工具函数
const formatTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return hours > 0 ? `${hours}:${minutes.toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}` 
                  : `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`
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

const getPlatformTagType = (platform: string) => {
  const types = {
    'douyin': 'danger',
    'weixin': 'success',
    'bilibili': 'primary',
    'youtube': 'warning'
  }
  return types[platform] || 'info'
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

const getLearningTagType = (status: string) => {
  const types = {
    'todo': 'info',
    'learning': 'warning',
    'completed': 'success'
  }
  return types[status] || 'info'
}

const getLearningText = (status: string) => {
  const texts = {
    'todo': '待学习',
    'learning': '学习中',
    'completed': '已完成'
  }
  return texts[status] || '未知'
}

// 防抖函数
function debounce(func: Function, wait: number) {
  let timeout: NodeJS.Timeout
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 页面加载
onMounted(async () => {
  await refreshData()
})
</script>

<style scoped>
.video-list-container {
  padding: 20px;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}
</style>