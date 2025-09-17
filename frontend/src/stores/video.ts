import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const useVideoStore = defineStore('video', () => {
  const videos = ref([])
  const loading = ref(false)
  
  // 添加视频
  const addVideo = async (videoData: any) => {
    try {
      const response = await api.post('/videos/process', videoData)
      return response.data
    } catch (error: any) {
      console.error('添加视频失败:', error)
      // 提取详细错误信息
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message || 
                          '未知错误'
      throw new Error(errorMessage)
    }
  }
  
  // 获取视频列表
  const getVideos = async (params: any) => {
    try {
      const response = await api.get('/videos/', { params })
      return response.data
    } catch (error) {
      console.error('获取视频列表失败:', error)
      throw error
    }
  }
  
  // 获取单个视频
  const getVideo = async (videoId: number) => {
    try {
      const response = await api.get(`/videos/${videoId}`)
      return response.data
    } catch (error) {
      console.error('获取视频详情失败:', error)
      throw error
    }
  }
  
  // 更新视频
  const updateVideo = async (videoId: number, updateData: any) => {
    try {
      const response = await api.put(`/videos/${videoId}`, updateData)
      return response.data
    } catch (error) {
      console.error('更新视频失败:', error)
      throw error
    }
  }
  
  // 删除视频
  const deleteVideo = async (videoId: number) => {
    try {
      await api.delete(`/videos/${videoId}`)
    } catch (error) {
      console.error('删除视频失败:', error)
      throw error
    }
  }
  
  // 获取字幕
  const getTranscript = async (videoId: number) => {
    try {
      const response = await api.get(`/transcripts/${videoId}`)
      return response.data
    } catch (error) {
      console.error('获取字幕失败:', error)
      throw error
    }
  }
  
  // 更新字幕
  const updateTranscript = async (videoId: number, transcriptData: any) => {
    try {
      const response = await api.put(`/transcripts/${videoId}`, transcriptData)
      return response.data
    } catch (error) {
      console.error('更新字幕失败:', error)
      throw error
    }
  }
  
  // 获取学习记录
  const getLearningRecord = async (videoId: number) => {
    try {
      const response = await api.get(`/learning/${videoId}`)
      return response.data
    } catch (error) {
      console.error('获取学习记录失败:', error)
      throw error
    }
  }
  
  // 更新学习记录
  const updateLearningRecord = async (videoId: number, recordData: any) => {
    try {
      const response = await api.put(`/learning/${videoId}`, recordData)
      return response.data
    } catch (error) {
      console.error('更新学习记录失败:', error)
      throw error
    }
  }
  
  // 获取统计数据
  const getStats = async () => {
    try {
      const response = await api.get('/learning/stats/overview')
      return response.data
    } catch (error) {
      console.error('获取统计数据失败:', error)
      throw error
    }
  }
  
  // 获取分类
  const getCategories = async () => {
    try {
      // 临时模拟数据，实际应该从API获取
      return [
        { id: 1, name: '编程教程', color: '#3B82F6' },
        { id: 2, name: '工具使用', color: '#10B981' },
        { id: 3, name: '框架学习', color: '#8B5CF6' },
        { id: 4, name: '待整理', color: '#6B7280' }
      ]
    } catch (error) {
      console.error('获取分类失败:', error)
      throw error
    }
  }
  
  // 获取最近视频
  const getRecentVideos = async (limit: number = 5) => {
    try {
      const response = await api.get(`/videos/?size=${limit}&status=completed`)
      return response.data.items
    } catch (error) {
      console.error('获取最近视频失败:', error)
      return []
    }
  }
  
  return {
    videos,
    loading,
    addVideo,
    getVideos,
    getVideo,
    updateVideo,
    deleteVideo,
    getTranscript,
    updateTranscript,
    getLearningRecord,
    updateLearningRecord,
    getStats,
    getCategories,
    getRecentVideos
  }
})