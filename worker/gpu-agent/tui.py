#!/usr/bin/env python3
"""
GPU TUI - Interactive GPU Selection Tool
使用 curses 库创建交互式 TUI 界面
"""

import curses
import subprocess
import re
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GPU:
    index: int
    name: str
    memory_total: int
    memory_used: int
    memory_percent: float
    utilization: float
    available: bool
    selected: bool = False


class GPUScreen:
    def __init__(self):
        self.gpus: List[GPU] = []
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
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # 可用 GPU
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # 不可用 GPU
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

    def get_gpu_info(self) -> List[GPU]:
        """获取 GPU 信息"""
        try:
            cmd = ["nvidia-smi",
                   "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                   "--format=csv,noheader,nounits"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            gpus = []
            for index, line in enumerate(result.stdout.strip().split('\n')):
                parts = line.split(',')
                if len(parts) >= 5:
                    name = parts[1].strip()
                    memory_total = int(parts[2].strip())
                    memory_used = int(parts[3].strip())
                    utilization = float(parts[4].strip())

                    memory_percent = (memory_used / memory_total) * 100
                    available = memory_percent <= 80.0 and utilization < 95.0

                    gpu = GPU(
                        index=index,
                        name=name,
                        memory_total=memory_total,
                        memory_used=memory_used,
                        memory_percent=memory_percent,
                        utilization=utilization,
                        available=available
                    )
                    gpus.append(gpu)

            return gpus

        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"Error getting GPU info: {e}")
            return []

    def draw_list_view(self):
        """绘制 GPU 列表视图"""
        self.screen.clear()

        # 绘制标题
        title = "Select GPUs (Space: select/unselect, Enter: confirm, Esc: quit)"
        title_x = (self.width - len(title)) // 2
        self.screen.addstr(0, title_x, title, curses.color_pair(4) | curses.A_BOLD)

        # 绘制 GPU 列表
        for i, gpu in enumerate(self.gpus):
            y = 2 + i

            # 如果当前行被选中，高亮显示
            if i == self.selected_idx:
                attr = curses.color_pair(3) | curses.A_BOLD
            else:
                attr = curses.color_pair(1) if gpu.available else curses.color_pair(2)

            # 选择状态
            select_symbol = "[✓]" if gpu.selected else "[ ]"

            # 状态符号
            status_symbol = "✓" if gpu.available else "✗"

            # GPU 信息
            line = f"{select_symbol} {status_symbol} [{gpu.index}] {gpu.name} - Memory: {gpu.memory_percent:.1f}% - Util: {gpu.utilization:.1f}%"

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

        # 显示选中的 GPU
        y = 2
        selected_count = 0

        for gpu in self.gpus:
            if gpu.selected:
                selected_count += 1
                line = f"✓ [{gpu.index}] {gpu.name}"
                if len(line) > self.width - 1:
                    line = line[:self.width - 1]
                self.screen.addstr(y, 0, line, curses.color_pair(1))
                y += 1

        if selected_count == 0:
            self.screen.addstr(y, 0, "No GPUs selected", curses.color_pair(2))
            y += 1

        # 显示统计信息
        stats = f"\nSelected {selected_count} GPUs"
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

        # 初始化 GPU 信息
        self.gpus = self.get_gpu_info()

        if not self.gpus:
            self.screen.addstr(0, 0, "No GPUs found", curses.color_pair(2))
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
                    elif key == curses.KEY_DOWN and self.selected_idx < len(self.gpus) - 1:
                        self.selected_idx += 1
                    elif key == ord(' '):
                        # 切换选择状态
                        if self.gpus[self.selected_idx].available:
                            self.gpus[self.selected_idx].selected = not self.gpus[self.selected_idx].selected
                        else:
                            # 显示错误信息
                            error_msg = f"Cannot select unavailable GPU: {self.selected_idx}"
                            self.screen.addstr(self.height - 2, 0, error_msg, curses.color_pair(2))
                            self.screen.refresh()
                            time.sleep(1)
                    elif key == curses.KEY_ENTER or key in (10, 13):
                        # 检查是否至少选择了一个 GPU
                        has_selection = any(gpu.selected for gpu in self.gpus)
                        if has_selection:
                            self.phase = "confirm"
                        else:
                            error_msg = "Please select at least one GPU"
                            self.screen.addstr(self.height - 2, 0, error_msg, curses.color_pair(2))
                            self.screen.refresh()
                            time.sleep(1)
                    elif key == 27:  # Esc
                        # 按 Esc 也保存选择（如果至少选择了一个）
                        selected_count = sum(1 for gpu in self.gpus if gpu.selected)
                        if selected_count > 0:
                            # 将选择结果写入临时文件
                            import os
                            # 使用用户可写的目录
                            run_dir = os.path.expanduser("~/.tokenmachine")
                            os.makedirs(run_dir, exist_ok=True)

                            with open(f"{run_dir}/selected_gpus.txt", "w") as f:
                                for gpu in self.gpus:
                                    if gpu.selected:
                                        f.write(f"{gpu.index}\n")

                            print("Selection saved!")
                            print("Selected GPUs:")
                            for gpu in self.gpus:
                                if gpu.selected:
                                    print(f"  - GPU {gpu.index}: {gpu.name}")
                        break

                elif self.phase == "confirm":
                    if key == curses.KEY_ENTER or key in (10, 13):
                        # 确认选择并退出
                        print("Selection saved!")
                        print("Selected GPUs:")
                        for gpu in self.gpus:
                            if gpu.selected:
                                print(f"  - GPU {gpu.index}: {gpu.name}")

                        # 将选择结果写入临时文件
                        import os
                        # 使用用户可写的目录
                        run_dir = os.path.expanduser("~/.tokenmachine")
                        os.makedirs(run_dir, exist_ok=True)

                        with open(f"{run_dir}/selected_gpus.txt", "w") as f:
                            for gpu in self.gpus:
                                if gpu.selected:
                                    f.write(f"{gpu.index}\n")

                        break
                    elif key == curses.KEY_BACKSPACE or key == 127:
                        # 返回列表视图
                        self.phase = "list"

        finally:
            self.cleanup_curses()


def main():
    """主函数"""
    print("Starting GPU TUI...")
    gpu_screen = GPUScreen()
    gpu_screen.run()


if __name__ == "__main__":
    main()