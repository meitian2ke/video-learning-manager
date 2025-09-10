<template>
  <div id="app">
    <el-container style="height: 100vh">
      <!-- 顶部导航 -->
      <el-header style="background-color: #545c64; color: #fff; line-height: 60px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h2 style="margin: 0;">📹 视频学习管理器</h2>
          <el-menu 
            :default-active="$route.path" 
            mode="horizontal" 
            background-color="#545c64"
            text-color="#fff"
            active-text-color="#ffd04b"
            router
          >
            <el-menu-item index="/">添加视频</el-menu-item>
            <el-menu-item index="/videos">视频列表</el-menu-item>
          </el-menu>
        </div>
      </el-header>

      <!-- 主内容区域 -->
      <el-main style="padding: 20px; background-color: #f5f5f5;">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
// 应用入口组件
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

body {
  margin: 0;
  padding: 0;
}
</style>