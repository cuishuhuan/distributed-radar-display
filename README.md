# 分布式雷达显控终端

浏览器端海图与船舶三维态势演示，附独立的 Windows/Python ZMQ 接收框架。

## 当前功能

- 海图底图切换、雷达扇区、船舶点选与高亮、目标详情、历史航迹。
- 24 艘仿真船舶，1–20 倍仿真速度，碰撞风险与最近会遇距离、时间显示。
- 船舶第一视角、通用驾驶舱、雷达小地图、方位条、日间/夜间模式。
- 9 种船模外形及图片、模型来源说明。
- ZMQ 公共消息头检查、消息接收状态与 HTTP 接口。

当前船舶运动和碰撞预测使用仿真数据。ISAR、光学和三维结果卡片使用示例图片。真实航迹、成像和识别载荷解码仍待正式协议样包接入；接收到 ZMQ 消息不表示真实目标已显示在海图上。

## 本地运行

需要 Python 3.10 或更新版本，以及支持 WebGL 的浏览器。默认不连接雷达数据源。

在项目根目录运行：

```powershell
python windows_zmq_bridge/bridge.py --config windows_zmq_bridge/settings.example.json --web-root web
```

打开 <http://127.0.0.1:8080/>。不要直接双击 HTML，图片与模型通过 HTTP `/assets/` 路径加载。网页无需 npm 安装或构建。

底图从外部地图服务加载，需要联网。高清 GLB 模型保留在 `web/`，首次加载耗时取决于网速及显卡性能。

## 接入 ZMQ

```powershell
python -m pip install -r requirements.txt
Copy-Item windows_zmq_bridge/settings.example.json windows_zmq_bridge/settings.json
```

编辑本机的 `settings.json`，按联调结果设置数据源，例如：

```json
{
  "host": "127.0.0.1",
  "port": 8080,
  "sources": [
    {"name": "数据处理机", "endpoint": "tcp://<实际IP>:<实际端口>", "topic": ""}
  ]
}
```

然后运行：

```powershell
python windows_zmq_bridge/bridge.py --web-root web
```

`/api/health` 和 `/api/state` 可查看接收状态。`protocol.py` 负责公共头与旧版回波检查；`bridge.py` 的 `MessageStore.accept()` 是后续接入已验证解码结果的位置。当前只接收消息，没有雷达控制指令发送接口。

## 文件位置

| 路径 | 用途 |
| --- | --- |
| `web/ui-index.html` | 海图、目标详情、三维场景、仿真与风险显示 |
| `web/bridge-scene.js` | 驾驶舱、仪表、方位条与示意岸景 |
| `web/*.glb` | 船舶模型，包含贴图 |
| `web/three.min.js`、`web/GLTFLoader.js` | 三维引擎与兼容修正后的模型加载器 |
| `windows_zmq_bridge/bridge.py` | HTTP 服务及 ZMQ 接收框架 |
| `windows_zmq_bridge/protocol.py` | 消息封装检查 |
| `web/ATTRIBUTION.txt` | 第三方图片与模型来源、许可说明 |

## 检查

安装 Node.js 后可运行已有自检；Node.js 不属于网页运行依赖。

```powershell
node web/check-ship-models.cjs
node web/check-bridge-scene.cjs
```

## 素材与配置

第三方模型、图片和引擎分别遵循各自的许可；本项目未对全部文件统一授予开源许可。素材来源记录见 `web/ATTRIBUTION.txt`。校徽、示例图片及协议代码在公开分发前需要另行确认适用范围。

本目录未包含服务器密码、SSH 密钥、部署脚本、原始回波数据、设计文档及本机数据源配置。
