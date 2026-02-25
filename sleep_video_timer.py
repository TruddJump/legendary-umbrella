#!/usr/bin/env python3
"""睡觉看视频定时关机/休眠小工具。"""

from __future__ import annotations

import datetime as dt
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk


class SleepTimerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("睡觉看视频定时助手")
        self.root.geometry("420x250")
        self.root.resizable(False, False)

        self.target_time: dt.datetime | None = None
        self.warn_opened = False

        self.hour_var = tk.StringVar()
        self.minute_var = tk.StringVar()
        self.action_var = tk.StringVar(value="休眠")
        self.status_var = tk.StringVar(value="请先选择时间和动作，然后点击【设定】。")
        self.countdown_var = tk.StringVar(value="")

        self._build_ui()
        self._set_default_time()

        self._tick()
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_taskbar)

    def _build_ui(self) -> None:
        wrapper = ttk.Frame(self.root, padding=14)
        wrapper.pack(fill="both", expand=True)

        ttk.Label(wrapper, text="目标时间（24小时制）").grid(row=0, column=0, sticky="w")

        hour_combo = ttk.Combobox(
            wrapper,
            textvariable=self.hour_var,
            values=[f"{h:02d}" for h in range(24)],
            width=8,
        )
        hour_combo.grid(row=0, column=1, sticky="w", padx=(10, 0))

        ttk.Label(wrapper, text=":").grid(row=0, column=2, sticky="w", padx=(6, 6))

        minute_combo = ttk.Combobox(
            wrapper,
            textvariable=self.minute_var,
            values=[f"{m:02d}" for m in range(60)],
            width=8,
        )
        minute_combo.grid(row=0, column=3, sticky="w")

        ttk.Label(wrapper, text="到点动作").grid(row=1, column=0, sticky="w", pady=(12, 0))
        action_combo = ttk.Combobox(
            wrapper,
            textvariable=self.action_var,
            values=["休眠", "关机"],
            state="readonly",
            width=10,
        )
        action_combo.grid(row=1, column=1, columnspan=3, sticky="w", padx=(10, 0), pady=(12, 0))

        set_btn = ttk.Button(wrapper, text="设定", command=self._on_set_clicked)
        set_btn.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(16, 0))

        status = ttk.Label(wrapper, textvariable=self.status_var, wraplength=380)
        status.grid(row=3, column=0, columnspan=4, sticky="w", pady=(14, 0))

        countdown = ttk.Label(wrapper, textvariable=self.countdown_var, foreground="#b45309")
        countdown.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _set_default_time(self) -> None:
        one_hour_later = dt.datetime.now() + dt.timedelta(hours=1)
        self.hour_var.set(f"{one_hour_later.hour:02d}")
        self.minute_var.set(f"{one_hour_later.minute:02d}")

    @staticmethod
    def _parse_time_value(raw: str, limit: int, field_name: str) -> int | None:
        value_text = raw.strip()
        if not value_text.isdigit():
            messagebox.showwarning("输入有误", f"{field_name}请输入 0-{limit} 的数字。")
            return None

        value = int(value_text)
        if not 0 <= value <= limit:
            messagebox.showwarning("输入有误", f"{field_name}超出范围，请输入 0-{limit}。")
            return None

        return value

    def _next_target_datetime(self, hour: int, minute: int) -> dt.datetime:
        now = dt.datetime.now()
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += dt.timedelta(days=1)
        return candidate

    def _on_set_clicked(self) -> None:
        hour = self._parse_time_value(self.hour_var.get(), 23, "小时")
        minute = self._parse_time_value(self.minute_var.get(), 59, "分钟")
        if hour is None or minute is None:
            return

        self.hour_var.set(f"{hour:02d}")
        self.minute_var.set(f"{minute:02d}")

        self.target_time = self._next_target_datetime(hour, minute)
        self.warn_opened = False

        self.status_var.set(
            f"设定成功：{self.target_time.strftime('%Y-%m-%d %H:%M')} 执行【{self.action_var.get()}】。"
        )
        self.countdown_var.set("")
        messagebox.showinfo("设定成功", "已为你保存设定，窗口将最小化到任务栏。")

        self._set_default_time()
        self._minimize_to_taskbar()

    def _open_warning_window(self) -> None:
        self.warn_opened = True
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(1200, lambda: self.root.attributes("-topmost", False))
        self.status_var.set("30秒后将执行动作。若你还醒着，请重新设定时间。")

    def _minimize_to_taskbar(self) -> None:
        self.root.iconify()

    def _execute_action(self) -> None:
        action = self.action_var.get().strip()
        self.status_var.set(f"时间到，准备执行：{action}")
        self.countdown_var.set("")

        try:
            system = platform.system().lower()
            if action == "关机":
                if system == "windows":
                    subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
                elif system == "darwin":
                    subprocess.run(["osascript", "-e", 'tell app "System Events" to shut down'], check=False)
                else:
                    subprocess.run(["shutdown", "-h", "now"], check=False)
            else:
                if system == "windows":
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
                elif system == "darwin":
                    subprocess.run(["pmset", "sleepnow"], check=False)
                else:
                    subprocess.run(["systemctl", "suspend"], check=False)
        finally:
            self.target_time = None
            self.warn_opened = False

    def _tick(self) -> None:
        if self.target_time:
            now = dt.datetime.now()
            seconds_left = int((self.target_time - now).total_seconds())

            if seconds_left <= 0:
                self._execute_action()
            else:
                if seconds_left <= 30 and not self.warn_opened:
                    self._open_warning_window()

                if self.warn_opened:
                    self.countdown_var.set(f"倒计时：{seconds_left} 秒")
                else:
                    self.countdown_var.set(
                        f"距离执行还有：{seconds_left // 3600:02d}:{(seconds_left % 3600) // 60:02d}:{seconds_left % 60:02d}"
                    )

        self.root.after(1000, self._tick)


def main() -> None:
    root = tk.Tk()
    app = SleepTimerApp(root)
    root.app = app  # type: ignore[attr-defined]
    root.mainloop()


if __name__ == "__main__":
    main()
