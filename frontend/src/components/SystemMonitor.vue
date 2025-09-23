<template>
  <div class="system-monitor">
    <el-card shadow="hover" class="monitor-card">
      <div class="monitor-header">
        <h3>🖥️ 系统状态</h3>
        <el-button 
          size="small" 
          @click="toggleExpanded"
          :icon="expanded ? 'ArrowUp' : 'ArrowDown'"
        >
          {{ expanded ? '收起' : '详情' }}
        </el-button>
      </div>
      
      <!-- 简洁状态栏 -->
      <div class="status-bar" v-if="!expanded">
        <div class="status-item">
          <span class="status-label">CPU:</span>
          <el-progress 
            :percentage="monitorData.cpu?.usage || 0" 
            :status="getProgressStatus(monitorData.cpu?.status)"
            :stroke-width="8"
            :show-text="false"
            style="width: 80px; margin-right: 8px;"
          />
          <span class="status-value">{{ monitorData.cpu?.usage || 0 }}%</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">GPU:</span>
          <el-progress 
            :percentage="monitorData.gpu?.usage || 0" 
            :status="getProgressStatus(monitorData.gpu?.status)"
            :stroke-width="8"
            :show-text="false"
            style="width: 80px; margin-right: 8px;"
          />
          <span class="status-value">{{ monitorData.gpu?.usage || 0 }}%</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">内存:</span>
          <el-progress 
            :percentage="monitorData.memory?.usage || 0" 
            :status="getProgressStatus(monitorData.memory?.status)"
            :stroke-width="8"
            :show-text="false"
            style="width: 80px; margin-right: 8px;"
          />
          <span class="status-value">{{ monitorData.memory?.usage || 0 }}%</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">转录:</span>
          <el-tag 
            :type="monitorData.transcription?.active ? 'success' : 'info'"
            effect="dark"
            size="small"
          >
            {{ monitorData.transcription?.active ? '运行中' : '空闲' }}
          </el-tag>
          <span class="status-value">{{ monitorData.transcription?.mode || 'CPU' }}</span>
        </div>
      </div>
      
      <!-- 详细监控面板 -->
      <div class="detailed-monitor" v-if="expanded">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="metric-card">
              <h4>🔥 CPU</h4>
              <el-progress 
                type="circle" 
                :percentage="monitorData.cpu?.usage || 0"
                :status="getProgressStatus(monitorData.cpu?.status)"
                :width="80"
              />
              <p class="metric-text">使用率: {{ monitorData.cpu?.usage || 0 }}%</p>
            </div>
          </el-col>
          
          <el-col :span="6">
            <div class="metric-card">
              <h4>🚀 GPU</h4>
              <el-progress 
                type="circle" 
                :percentage="monitorData.gpu?.usage || 0"
                :status="getProgressStatus(monitorData.gpu?.status)"
                :width="80"
              />
              <p class="metric-text">
                使用率: {{ monitorData.gpu?.usage || 0 }}%<br>
                显存: {{ monitorData.gpu?.memory || 0 }}%
              </p>
            </div>
          </el-col>
          
          <el-col :span="6">
            <div class="metric-card">
              <h4>💾 内存</h4>
              <el-progress 
                type="circle" 
                :percentage="monitorData.memory?.usage || 0"
                :status="getProgressStatus(monitorData.memory?.status)"
                :width="80"
              />
              <p class="metric-text">
                {{ monitorData.memory?.used || 0 }}GB / {{ monitorData.memory?.total || 0 }}GB
              </p>
            </div>
          </el-col>
          
          <el-col :span="6">
            <div class="metric-card">
              <h4>⚡ 转录</h4>
              <div class="transcription-status">
                <el-tag 
                  :type="monitorData.transcription?.active ? 'success' : 'info'"
                  effect="dark"
                  size="large"
                >
                  {{ monitorData.transcription?.active ? '🔥 运行中' : '💤 空闲' }}
                </el-tag>
                <p class="metric-text">
                  模式: {{ monitorData.transcription?.mode || 'CPU' }}<br>
                  并发: {{ monitorData.transcription?.max_concurrent || 3 }}
                </p>
              </div>
            </div>
          </el-col>
        </el-row>
        
        <div class="monitor-actions">
          <el-button 
            type="primary" 
            size="small" 
            @click="openGpuMonitor"
            v-if="monitorData.gpu?.available"
          >
            🖥️ GPU详情
          </el-button>
          <el-button 
            type="info" 
            size="small" 
            @click="refreshData"
          >
            🔄 刷新
          </el-button>
        </div>
      </div>
      
      <!-- 错误状态 -->
      <div v-if="error" class="error-status">
        <el-alert 
          title="监控数据获取失败" 
          :description="error" 
          type="warning" 
          show-icon 
          :closable="false"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const monitorData = ref({})
const error = ref('')
const expanded = ref(false)
let refreshInterval = null

const toggleExpanded = () => {
  expanded.value = !expanded.value
}

const fetchMonitorData = async () => {
  try {
    const response = await axios.get('/api/monitor/lite')
    monitorData.value = response.data
    error.value = ''
  } catch (err) {
    error.value = err.message || '无法获取监控数据'
    console.error('Monitor data fetch error:', err)
  }
}

const refreshData = () => {
  fetchMonitorData()
}

const openGpuMonitor = () => {
  window.open('/api/gpu/status', '_blank')
}

const getProgressStatus = (status) => {
  switch (status) {
    case 'high': return 'exception'
    case 'normal': return 'warning'
    case 'low': return 'success'
    default: return ''
  }
}

onMounted(() => {
  fetchMonitorData()
  // 每5秒刷新一次
  refreshInterval = setInterval(fetchMonitorData, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.system-monitor {
  margin-bottom: 20px;
}

.monitor-card {
  border-radius: 12px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.monitor-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 150px;
}

.status-label {
  font-weight: 600;
  color: #34495e;
  min-width: 40px;
}

.status-value {
  font-weight: 600;
  color: #2c3e50;
  min-width: 40px;
  text-align: right;
}

.detailed-monitor {
  margin-top: 20px;
}

.metric-card {
  text-align: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

.metric-card h4 {
  margin: 0 0 15px 0;
  color: #34495e;
  font-size: 16px;
}

.metric-text {
  margin: 10px 0 0 0;
  color: #7f8c8d;
  font-size: 12px;
  line-height: 1.4;
}

.transcription-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.monitor-actions {
  margin-top: 20px;
  text-align: center;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.error-status {
  margin-top: 15px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .status-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .status-item {
    min-width: auto;
    justify-content: space-between;
  }
}
</style>