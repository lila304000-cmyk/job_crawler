#!/usr/bin/env python3
"""本地启动脚本：同时启动 FastAPI 后端并托管前端静态资源。"""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")


def main():
    os.chdir(BACKEND_DIR)
    sys.path.insert(0, BACKEND_DIR)

    try:
        import uvicorn
    except ImportError:
        print("[ERROR] 缺少依赖，请先执行: pip install -r backend/requirements.txt")
        sys.exit(1)

    print("=" * 60)
    print("Job Crawler Web 正在启动...")
    print("访问地址: http://localhost:8000")
    print("API 文档:  http://localhost:8000/api/docs")
    print("默认账号: admin / admin123")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
