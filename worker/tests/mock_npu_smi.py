#!/usr/bin/env python3
"""
Mock npu-smi command for testing Ascend Agent without real NPU hardware.

模拟 npu-smi 命令，输出符合昇腾 NPU 格式的假数据。
支持 list 和 info 子命令。
"""

import argparse
import random
import sys
import time
from typing import List, Dict, Optional


# 模拟 NPU 设备配置
MOCK_NPUS = [
    {
        "id": 0,
        "name": "Ascend910A",
        "board_id": "D111P",
        "status": "Normal",
        "aic_core": {"usage": 45, "max": 100},
        "aic_memory": {"used": 16384, "total": 32768},  # MB
        "hbm_memory": {"used": 16384, "total": 32768},  # MB
        "temperature": 45,
        "power": 150,
    },
    {
        "id": 1,
        "name": "Ascend910A",
        "board_id": "D111P",
        "status": "Normal",
        "aic_core": {"usage": 30, "max": 100},
        "aic_memory": {"used": 8192, "total": 32768},
        "hbm_memory": {"used": 8192, "total": 32768},
        "temperature": 42,
        "power": 120,
    },
]


def cmd_list(format_type: str = "table") -> str:
    """模拟 npu-smi list 命令"""
    if format_type == "csv":
        lines = ["Index,Name,Status,AIC(%),Memory,MEM(%)"]
        for npu in MOCK_NPUS:
            mem_pct = (npu["hbm_memory"]["used"] / npu["hbm_memory"]["total"]) * 100
            lines.append(f"{npu['id']},{npu['name']},{npu['status']},{npu['aic_core']['usage']}%,{npu['hbm_memory']['used']}MB/{npu['hbm_memory']['total']}MB,{mem_pct:.0f}%")
        return "\n".join(lines)
    else:
        # 默认表格格式
        header = f"{'NPU ID':<8} {'Name':<12} {'Health':<8} {'AIC(%)':<8} {'Memory':<25} {'Temp':<6} {'Power':<8}"
        separator = "-" * len(header)
        lines = [header, separator]
        for npu in MOCK_NPUS:
            mem_str = f"{npu['hbm_memory']['used']}MB/{npu['hbm_memory']['total']}MB"
            line = f"{npu['id']:<8} {npu['name']:<12} {npu['status']:<8} {npu['aic_core']['usage']:<8} {mem_str:<25} {npu['temperature']:<6} {npu['power']:<8}"
            lines.append(line)
        return "\n".join(lines)


def cmd_info(npu_id: int = 0, format_type: str = "table") -> str:
    """模拟 npu-smi info 命令"""
    if npu_id >= len(MOCK_NPUS):
        return f"npu-smi: info: Failed to get NPU info. NPU {npu_id} not found."

    npu = MOCK_NPUS[npu_id]

    if format_type == "csv":
        lines = ["NPU ID,Name,Status,AIC(%),HBM Memory Used,HBM Memory Total,Temperature,Power"]
        mem_pct = (npu["hbm_memory"]["used"] / npu["hbm_memory"]["total"]) * 100
        lines.append(f"{npu['id']},{npu['name']},{npu['status']},{npu['aic_core']['usage']}%,{npu['hbm_memory']['used']}MB,{npu['hbm_memory']['total']}MB,{npu['temperature']},{npu['power']}")
        return "\n".join(lines)
    elif format_type == "json":
        import json
        return json.dumps(npu, indent=2)
    else:
        # 表格格式
        mem_pct = (npu["hbm_memory"]["used"] / npu["hbm_memory"]["total"]) * 100
        lines = [
            f"+------------------------------------------------------+",
            f"| npu-smi {npu_id} information                            |",
            f"+------------------------------------------------------+",
            f"| Version: 1.0                                          |",
            f"| Driver Version: 1.0.0                                 |",
            f"+------------------------------------------------------+",
            f"| Board ID: {npu['board_id']:<33} |",
            f"| NPU Name: {npu['name']:<35} |",
            f"+------------------------------------------------------+",
            f"| Status: {npu['status']:<39} |",
            f"+------------------------------------------------------+",
            f"| AICore Usage: {npu['aic_core']['usage']:<3}% / 100%                        |",
            f"| HBM Memory: {npu['hbm_memory']['used']:<5} MB / {npu['hbm_memory']['total']:<5} MB ({mem_pct:.0f}%)           |",
            f"+------------------------------------------------------+",
            f"| Temperature: {npu['temperature']:<3}°C                                  |",
            f"| Power: {npu['power']:<4} W                                        |",
            f"+------------------------------------------------------+",
        ]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Mock npu-smi for testing")
    parser.add_argument("command", choices=["list", "info"], help="Command to execute")
    parser.add_argument("-i", "--id", type=int, default=0, help="NPU ID for info command")
    parser.add_argument("-f", "--format", choices=["table", "csv", "json"], default="table", help="Output format")
    parser.add_argument("-l", "--query", help="Query specific fields (npu-smi info compatible)")

    args = parser.parse_args()

    if args.command == "list":
        output = cmd_list(args.format)
    elif args.command == "info":
        output = cmd_info(args.id, args.format)
    else:
        output = "Unknown command"

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
