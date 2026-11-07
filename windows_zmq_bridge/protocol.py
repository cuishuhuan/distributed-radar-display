"""Radar ZMQ envelope and conservative message inspection.

Payload decoders for tracks, images and recognition are intentionally pending
real captures from their publishers. Never invent target values from headers.
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass


HEADER_BYTES = 12
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
MESSAGE_NAMES = {
    (1, 1): "雷达节点状态",
    (2, 1): "控制参数",
    (2, 26): "联调回波旧版",
    (3, 1): "原始回波",
    (3, 2): "一次处理点迹",
    (3, 3): "目标态势与航迹",
    (3, 4): "船舶成像结果",
    (3, 5): "窄带频谱",
    (3, 6): "极化特征",
    (3, 7): "船舶识别结果",
    (3, 8): "AIS 航迹",
    (3, 9): "北斗航迹",
    (4, 1): "分机状态与告警",
}


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class Envelope:
    declared_length: int
    destination_id: int
    source_id: int
    type_id: int
    content_id: int


def parse_envelope(message: bytes) -> tuple[Envelope, memoryview]:
    if len(message) < HEADER_BYTES:
        raise ProtocolError(f"消息不足 {HEADER_BYTES} 字节")
    if message[:2] != b"\x1b\x1c":
        raise ProtocolError("前导符不是 1B 1C")
    declared_length = struct.unpack_from(">I", message, 4)[0]
    if declared_length > MAX_PAYLOAD_BYTES:
        raise ProtocolError(f"声明长度超过上限：{declared_length}")
    actual_length = len(message) - HEADER_BYTES
    if declared_length != actual_length:
        raise ProtocolError(
            f"长度不符：声明 {declared_length}，实际 {actual_length}"
        )
    envelope = Envelope(declared_length, *message[8:12])
    return envelope, memoryview(message)[HEADER_BYTES:]


def inspect_legacy_echo(payload: memoryview) -> dict:
    """Inspect the test format: int32 radar ID, then 512-byte-head echo frames."""
    if len(payload) < 4:
        raise ProtocolError("联调回波缺少雷达编号")
    radar_id = struct.unpack_from("<i", payload, 0)[0]
    result = {"radarId": radar_id, "payloadBytes": len(payload)}
    if len(payload) < 4 + 32:
        return result
    frame_start = 4
    magic1, magic2 = struct.unpack_from("<II", payload, frame_start)
    if (magic1, magic2) != (0x11FFFF11, 0x20230211):
        result["note"] = "首帧标志未匹配，暂不解析回波"
        return result
    frame_bytes = struct.unpack_from("<I", payload, frame_start + 20)[0]
    if frame_bytes < 512 or (frame_bytes - 512) % 8:
        raise ProtocolError(f"异常回波帧长：{frame_bytes}")
    declared_frames = (len(payload) - 4) // frame_bytes
    matching_headers = 0
    first_frame = None
    for index in range(declared_frames):
        offset = frame_start + index * frame_bytes
        if struct.unpack_from("<II", payload, offset) != (0x11FFFF11, 0x20230211):
            break
        if struct.unpack_from("<I", payload, offset + 20)[0] != frame_bytes:
            break
        if first_frame is None:
            first_frame = struct.unpack_from("<I", payload, offset + 16)[0]
        matching_headers += 1
    result.update(
        frameBytes=frame_bytes,
        expectedFrames=declared_frames,
        matchingFrameHeaders=matching_headers,
        firstFrameNumber=first_frame,
        samplePointsPerFrame=(frame_bytes - 512) // 8,
    )
    if matching_headers != declared_frames:
        result["note"] = "消息中并非所有预期帧都具有有效帧头；检查录制是否截断或填零"
    return result


def inspect_message(message: bytes) -> dict:
    envelope, payload = parse_envelope(message)
    result = {
        "kind": MESSAGE_NAMES.get(
            (envelope.type_id, envelope.content_id), "未识别的消息类型"
        ),
        "header": asdict(envelope),
        "payloadBytes": len(payload),
        "decoded": False,
    }
    if (envelope.type_id, envelope.content_id) == (2, 26):
        result["summary"] = inspect_legacy_echo(payload)
    else:
        result["summary"] = {
            "note": "已接收并校验消息头；等待此类消息的真实样包后补充字段解析"
        }
    return result
