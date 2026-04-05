"""
支持 python -m src.web 启动 Web 服务器。

使用 uvicorn 启动 FastAPI 应用，默认监听 0.0.0.0:8000。
"""

import uvicorn


def main():
    """启动 Web 服务器。"""
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
