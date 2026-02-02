#!/usr/bin/env python3
"""
Ascend NPU TUI - Interactive Ascend Device Selection Tool
使用 curses 库创建交互式 TUI 界面
适配华为昇腾 NPU 设备
"""

import curses
import subprocess
import re
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AscendNPU:
    """昇腾 NPU 设备信息"""
    index: int              # NPU 索引
    name: str               # NPU 名称 (如 Ascend910)
    memory_total: int       # 总内存 (MB)
    memory_used: int        # 已用内存 (MB)
    memory_percent: float   # 内存使用百分比
    utilization: float      # 计算利用率
    available: bool         # 是否可用 (<=80%内存 且 <95%利用率)
    selected: bool = False  # 是否被选中


class AscendScreen:
    """昇腾 NPU 选择 TUI 界面"""

    def __init__(self):
        self.npus: List[AscendNPU] = []
        self.selected_idx = 0
        self.phase = "list"  # "list" or "confirm"
        self.screen = None
        self.height = 0
        self.width = 0

    def init_curses(self):
        """初始化 curses 设置"""
        self.screen = curses.initscr()
        curses.cbreak()
        curses.noecho()
        self.screen.keypad(True)
        curses.curs_set(0)  # 隐藏光标

        # 获取屏幕尺寸
        self.height, self.width = self.screen.getmaxyx()

        # 设置颜色对
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # 可用 NPU
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # 不可用 NPU
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)    # 选中状态
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # 标题

    def cleanup_curses(self):
        """清理 curses 设置"""
        if self.screen:
            curses.curs_set(1)
            self.screen.keypad(False)
            curses.echo()
            curses.nocbreak()
            curses.endwin()

    def get_npu_info(self) -> List[AscendNPU]:
        """获取 NPU 信息 (使用 npu-smi)"""
        try:
            # 使用 npu-smi 获取 NPU 信息
            cmd = [
                "npu-smi",
                "info",
                "--query",
                "board,index,status,memory,utilization",
                "-f", "csv"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            npus = []
            lines = result.stdout.strip().split('\n')

            # 跳过标题行
            for index, line in enumerate(lines[1:], start=0):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    name = parts[0].strip()  # 板卡名称
                    # 尝试解析索引
                    try:
                        idx = int(parts[1].strip())
                    except ValueError:
                        idx = index

                    status = parts[2].strip().lower()
                    if status != "normal":
                        continue  # 跳过不正常的 NPU

                    # 解析内存 (格式: "16384MB / 32768MB")
                    memory_match = re.match(r'(\d+)\s*MB\s*/\s*(\d+)\s*MB', parts[3].strip())
                    if memory_match:
                        memory_used = int(memory_match.group(1))
                        memory_total = int(memory_match.group(2))
                    else:
                        memory_used = 0
                        memory_total = 32768  # 默认 Ascend910

                    # 解析利用率 (格式: "10%")
                    util_match = re.match(r'(\d+)%', parts[4].strip())
                    utilization = float(util_match.group(1)) if util_match else 0.0

                    memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
                    available = memory_percent <= 80.0 and utilization < 95.0

                    npu = AscendNPU(
                        index=idx,
                        name=name,
                        memory_total=memory_total,
                        memory_used=memory_used,
                        memory_percent=memory_percent,
                        utilization=utilization,
                        available=available
                    )
                    npus.append(npu)

            return npus

        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Error getting NPU info: {e}")
            # 尝试备用方法：使用 npu-smi list
            return self._get_npu_info_fallback()

    def _get_npu_info_fallback(self) -> List[AscendNPU]:
        """备用方法：使用 npu-smi list 获取 NPU 信息"""
        try:
            cmd = ["npu-smi", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            npus = []
            for line in result.stdout.strip().split('\n'):
                # 匹配 NPU 信息行 (如 "0  Ascend910  Normal  10%  16384MB / 32768MB")
                match = re.match(
                    r'(\d+)\s+(\w+)\s+(\w+)\s+(\d+)%\s+(\d+)MB\s*/\s*(\d+)MB',
                    line.strip()
                )
                if match:
                    idx = int(match.group(1))
                    name = match.group(2)
                    status = match.group(3)
                    utilization = float(match.group(4))
                    memory_used = int(match.group(5))
                    memory_total = int(match.group(6))

                    if status != "Normal":
                        continue

                    memory_percent = (memory_used / memory_total) * 100
                    available = memory_percent <= 80.0 and utilization < 95.0

                    npus.append(AscendNPU(
                        index=idx,
                        name=name,
                        memory_total=memory_total,
                        memory_used=memory_used,
                        memory_percent=memory_percent,
                        utilization=utilization,
                        available=available
                    ))

            return npus

        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Error in fallback NPU info: {e}")
            return []

    def draw_list_view(self):
        """绘制 NPU 列表视图"""
        self.screen.clear()

        # 绘制标题
        title = "Select Ascend NPs (Space: select/unselect, Enter: confirm, Esc: quit)"
        title_x = (self.width - len(title)) // 2
        self.screen.addstr(0, title_x, title, curses.color_pair(4) | curses.A_BOLD)

        # 绘制 NPU 列表
        for i, npu in enumerate(self.npus):
            y = 2 + i

            # 如果当前行被选中，高亮显示
            if i == self.selected_idx:
                attr = curses.color_pair(3) | curses.A_BOLD
            else:
                attr = curses.color_pair(1) if npu.available else curses.color_pair(2)

            # 选择状态
            select_symbol = "[✓]" if npu.selected else "[ ]"

            # 状态符号
            status_symbol = "✓" if npu.available else "✗"

            # NPU 信息
            line = f"{select_symbol} {status_symbol} [{npu.index}] {npu.name} - Memory: {npu.memory_percent:.1f}% - Util: {npu.utilization:.1f}%"

            # 确保行不超过屏幕宽度
            if len(line) > self.width - 1:
                line = line[:self.width - 1]

            self.screen.addstr(y, 0, line, attr)

        # 绘制帮助信息
        help_text = "↑↓ Navigate | Space Select | Enter Confirm | Esc Quit"
        help_x = (self.width - len(help_text)) // 2
        self.screen.addstr(self.height - 1, help_x, help_text, curses.color_pair(4))

        self.screen.refresh()

    def draw_confirm_view(self):
        """绘制确认视图"""
        self.screen.clear()

        # 绘制标题
        title = "Confirm Selection"
        title_x = (self.width - len(title)) // 2
        self.screen.addstr(0, title_x, title, curses.color_pair(4) | curses.A_BOLD)

        # 显示选中的 NPU
        y = 2
        selected_count = 0

        for npu in self.npus:
            if npu.selected:
                selected_count += 1
                line = f"✓ [{npu.index}] {npu.name}"
                if len(line) > self.width - 1:
                    line = line[:self.width - 1]
                self.screen.addstr(y, 0, line, curses.color_pair(1))
                y += 1

        if selected_count == 0:
            self.screen.addstr(y, 0, "No NPs selected", curses.color_pair(2))
            y += 1

        # 显示统计信息
        stats = f"\nSelected {selected_count} NPs"
        stats_x = (self.width - len(stats)) // 2
        self.screen.addstr(y, stats_x, stats, curses.color_pair(4))
        y += 1

        # 显示帮助信息
        help_text = "Enter: Confirm, Backspace: Back"
        help_x = (self.width - len(help_text)) // 2
        self.screen.addstr(y + 1, help_x, help_text, curses.color_pair(4))

        self.screen.refresh()

    def run(self):
        """运行 TUI"""
        self.init_curses()

        # 初始化 NPU 信息
        self.npus = self.get_npu_info()

        if not self.npus:
            self.screen.addstr(0, 0, "No Ascend NPs found. Please check CANN installation.", curses.color_pair(2))
            self.screen.refresh()
            self.screen.getch()
            self.cleanup_curses()
            return

        try:
            while True:
                if self.phase == "list":
                    self.draw_list_view()
                elif self.phase == "confirm":
                    self.draw_confirm_view()

                # 处理输入
                key = self.screen.getch()

                if self.phase == "list":
                    if key == curses.KEY_UP and self.selected_idx > 0:
                        self.selected_idx -= 1
                    elif key == curses.KEY_DOWN and self.selected_idx < len(self.npus) - 1:
                        self.selected_idx += 1
                    elif key == ord(' '):
                        # 切换选择状态
                        if self.npus[self.selected_idx].available:
                            self.npus[self.selected_idx].selected = not self.npus[self.selected_idx].selected
                        else:
                            # 显示错误信息
                            error_msg = f"Cannot select unavailable NPU: {self.selected_idx}"
                            self.screen.addstr(self.height - 2, 0, error_msg, curses.color_pair(2))
                            self.screen.refresh()
                            time.sleep(1)
                    elif key == curses.KEY_ENTER or key in (10, 13):
                        # 检查是否至少选择了一个 NPU
                        has_selection = any(npu.selected for npu in self.npus)
                        if has_selection:
                            self.phase = "confirm"
                        else:
                            error_msg = "Please select at least one NPU"
                            self.screen.addstr(self.height - 2, 0, error_msg, curses.color_pair(2))
                            self.screen.refresh()
                            time.sleep(1)
                    elif key == 27:  # Esc
                        # 按 Esc 也保存选择（如果至少选择了一个）
                        selected_count = sum(1 for npu in self.npus if npu.selected)
                        if selected_count > 0:
                            # 将选择结果写入临时文件
                            import os
                            # 使用用户可写的目录
                            run_dir = os.path.expanduser("~/.tokenmachine")
                            os.makedirs(run_dir, exist_ok=True)

                            with open(f"{run_dir}/selected_npus.txt", "w") as f:
                                for npu in self.npus:
                                    if npu.selected:
                                        f.write(f"{npu.index}\n")

                            print("Selection saved!")
                            print("Selected NPs:")
                            for npu in self.npus:
                                if npu.selected:
                                    print(f"  - NPU {npu.index}: {npu.name}")
                        break

                elif self.phase == "confirm":
                    if key == curses.KEY_ENTER or key in (10, 13):
                        # 确认选择并退出
                        print("Selection saved!")
                        print("Selected NPs:")
                        for npu in self.npus:
                            if npu.selected:
                                print(f"  - NPU {npu.index}: {npu.name}")

                        # 将选择结果写入临时文件
                        import os
                        # 使用用户可写的目录
                        run_dir = os.path.expanduser("~/.tokenmachine")
                        os.makedirs(run_dir, exist_ok=True)

                        with open(f"{run_dir}/selected_npus.txt", "w") as f:
                            for npu in self.npus:
                                if npu.selected:
                                    f.write(f"{npu.index}\n")

                        break
                    elif key == curses.KEY_BACKSPACE or key == 127:
                        # 返回列表视图
                        self.phase = "list"

        finally:
            self.cleanup_curses()


def main():
    """主函数"""
    print("Starting Ascend NPU TUI...")
    ascend_screen = AscendScreen()
    ascend_screen.run()


if __name__ == "__main__":
    main()
