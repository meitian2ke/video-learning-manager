from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import subprocess
import json
import re

router = APIRouter()

@router.get("/gpu/status", response_class=HTMLResponse)
async def gpu_monitor_page():
    """GPU监控页面"""
    
    try:
        # 获取GPU信息
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpu_data = result.stdout.strip().split(', ')
            gpu_info = {
                'name': gpu_data[0],
                'memory_total': int(gpu_data[1]),
                'memory_used': int(gpu_data[2]),
                'memory_free': int(gpu_data[3]),
                'utilization': int(gpu_data[4]),
                'temperature': int(gpu_data[5]),
                'power_draw': float(gpu_data[6]) if gpu_data[6] != '[Not Supported]' else 0
            }
        else:
            gpu_info = None
            
    except Exception:
        gpu_info = None
    
    # 获取进程信息
    processes = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                parts = line.split(', ')
                if len(parts) >= 3:
                    processes.append({
                        'pid': parts[0],
                        'name': parts[1],
                        'memory': int(parts[2])
                    })
    except Exception:
        pass

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GPU 监控面板</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .gpu-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric {{
                text-align: center;
            }}
            .metric-value {{
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .metric-label {{
                font-size: 0.9em;
                opacity: 0.8;
            }}
            .progress-bar {{
                width: 100%;
                height: 20px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #FFC107, #FF5722);
                transition: width 0.3s ease;
            }}
            .processes-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            .processes-table th,
            .processes-table td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .processes-table th {{
                background: rgba(255, 255, 255, 0.1);
            }}
            .status-indicator {{
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            .status-online {{ background: #4CAF50; }}
            .status-offline {{ background: #FF5722; }}
            .refresh-btn {{
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                margin: 20px 10px;
                transition: all 0.3s ease;
            }}
            .refresh-btn:hover {{
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }}
        </style>
        <script>
            function refreshPage() {{
                location.reload();
            }}
            // 自动刷新
            setInterval(refreshPage, 5000);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 GPU 监控面板</h1>
                <p>实时监控 NVIDIA GPU 状态</p>
                <button class="refresh-btn" onclick="refreshPage()">🔄 手动刷新</button>
                <button class="refresh-btn" onclick="window.location.href='/'">🏠 返回首页</button>
            </div>
            
            {"" if gpu_info else '<div class="card"><h2>❌ GPU 未检测到</h2><p>请确保 NVIDIA 驱动已安装且 nvidia-smi 可用</p></div>'}
            
            {f'''
            <div class="card">
                <h2>
                    <span class="status-indicator status-online"></span>
                    {gpu_info['name']}
                </h2>
                
                <div class="gpu-grid">
                    <div class="metric">
                        <div class="metric-value">{gpu_info['utilization']}%</div>
                        <div class="metric-label">GPU 使用率</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {gpu_info['utilization']}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-value">{gpu_info['memory_used']} MB</div>
                        <div class="metric-label">显存使用</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(gpu_info['memory_used'] / gpu_info['memory_total'] * 100):.1f}%"></div>
                        </div>
                        <small>{gpu_info['memory_used']}/{gpu_info['memory_total']} MB</small>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-value">{gpu_info['temperature']}°C</div>
                        <div class="metric-label">温度</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {min(gpu_info['temperature'], 100)}%"></div>
                        </div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-value">{gpu_info['power_draw']:.1f}W</div>
                        <div class="metric-label">功耗</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🔧 GPU 进程</h3>
                {f"""
                <table class="processes-table">
                    <thead>
                        <tr>
                            <th>进程ID</th>
                            <th>进程名称</th>
                            <th>显存占用</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr><td>{p['pid']}</td><td>{p['name']}</td><td>{p['memory']} MB</td></tr>" for p in processes]) if processes else "<tr><td colspan='3' style='text-align: center; opacity: 0.7;'>无运行进程</td></tr>"}
                    </tbody>
                </table>
                """ if processes is not None else "<p>无法获取进程信息</p>"}
            </div>
            ''' if gpu_info else ''}
            
            <div class="card">
                <h3>📊 系统信息</h3>
                <p><strong>最后更新:</strong> <span id="timestamp">{subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}</span></p>
                <p><strong>自动刷新:</strong> 每5秒</p>
                <p><strong>监控地址:</strong> http://192.168.0.106/api/gpu/status</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


@router.get("/gpu/json")
async def gpu_status_json():
    """返回JSON格式的GPU状态"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpu_data = result.stdout.strip().split(', ')
            return {
                "status": "online",
                "name": gpu_data[0],
                "memory_total": int(gpu_data[1]),
                "memory_used": int(gpu_data[2]),
                "utilization": int(gpu_data[3]),
                "temperature": int(gpu_data[4])
            }
        else:
            return {"status": "error", "message": "nvidia-smi failed"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}