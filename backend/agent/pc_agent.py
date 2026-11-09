# backend/agent/pc_agent.py — Atlas 7.0 PC/System Agent
# Handles: optimize, clean, battery, shutdown, restart, lock, wifi, bluetooth, system status

import subprocess
import platform
import os
import psutil
import shutil
from typing import Dict, List, Optional
from datetime import datetime
from .base_agent import BaseAgent


class PCAgent(BaseAgent):
    """PC/System control agent - manages all system-level operations"""

    def __init__(self):
        super().__init__(
            name="PC Agent",
            description="Manages PC optimization, system control, battery, network, and diagnostics"
        )
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_linux = self.system == "Linux"
        self.is_mac = self.system == "Darwin"

    def get_capabilities(self) -> List[str]:
        return [
            "optimize_pc", "clean_pc", "shutdown", "restart", "lock", 
            "sleep", "battery_status", "system_status", "wifi_status",
            "wifi_toggle", "bluetooth_status", "bluetooth_toggle",
            "disk_cleanup", "ram_cleanup", "startup_apps", "process_manager"
        ]

    # ========== SYSTEM CONTROL ==========

    def shutdown(self, delay: int = 0) -> Dict:
        """Shutdown the system"""
        try:
            msg = f"System shutting down{f' in {delay} seconds' if delay else ''}..."
            if self.is_windows:
                cmd = f"shutdown /s {f'/t {delay}' if delay else '/t 0'}"
                subprocess.Popen(cmd, shell=True)
            elif self.is_linux:
                cmd = f"shutdown {'+' + str(delay//60) if delay else 'now'}"
                subprocess.Popen(cmd, shell=True)
            elif self.is_mac:
                cmd = f"shutdown -h {'+' + str(delay//60) if delay else 'now'}"
                subprocess.Popen(cmd, shell=True)

            return {"success": True, "message": f"🔴 {msg}", "action": "shutdown", "delay": delay}
        except Exception as e:
            return {"success": False, "message": f"❌ Shutdown failed: {str(e)}"}

    def restart(self, delay: int = 0) -> Dict:
        """Restart the system"""
        try:
            msg = f"System restarting{f' in {delay} seconds' if delay else ''}..."
            if self.is_windows:
                cmd = f"shutdown /r {f'/t {delay}' if delay else '/t 0'}"
                subprocess.Popen(cmd, shell=True)
            elif self.is_linux:
                cmd = f"reboot"
                subprocess.Popen(cmd, shell=True)
            elif self.is_mac:
                cmd = f"reboot"
                subprocess.Popen(cmd, shell=True)

            return {"success": True, "message": f"🔄 {msg}", "action": "restart", "delay": delay}
        except Exception as e:
            return {"success": False, "message": f"❌ Restart failed: {str(e)}"}

    def lock(self) -> Dict:
        """Lock the screen"""
        try:
            if self.is_windows:
                subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            elif self.is_linux:
                # Try multiple locker methods
                lockers = ["gnome-screensaver-command -l", "loginctl lock-session", "xscreensaver-command -lock"]
                for locker in lockers:
                    try:
                        subprocess.Popen(locker, shell=True)
                        break
                    except:
                        continue
            elif self.is_mac:
                subprocess.Popen("pmset displaysleepnow", shell=True)

            return {"success": True, "message": "🔒 System locked successfully", "action": "lock"}
        except Exception as e:
            return {"success": False, "message": f"❌ Lock failed: {str(e)}"}

    def sleep(self) -> Dict:
        """Put system to sleep"""
        try:
            if self.is_windows:
                subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            elif self.is_linux:
                subprocess.Popen("systemctl suspend", shell=True)
            elif self.is_mac:
                subprocess.Popen("pmset sleepnow", shell=True)

            return {"success": True, "message": "💤 System going to sleep", "action": "sleep"}
        except Exception as e:
            return {"success": False, "message": f"❌ Sleep failed: {str(e)}"}

    # ========== OPTIMIZATION ==========

    def optimize_pc(self) -> Dict:
        """Full PC optimization"""
        results = []

        # 1. RAM cleanup
        ram_result = self._clean_ram()
        results.append(ram_result)

        # 2. Disk cleanup
        disk_result = self._clean_disk()
        results.append(disk_result)

        # 3. Clear temp files
        temp_result = self._clean_temp()
        results.append(temp_result)

        # 4. Empty recycle bin
        bin_result = self._empty_recycle_bin()
        results.append(bin_result)

        # Get final stats
        stats = self._get_system_stats()

        return {
            "success": True,
            "message": f"⚡ PC Optimized!\n🧹 RAM: {ram_result.get('freed', 'N/A')}\n💾 Disk: {disk_result.get('freed', 'N/A')}\n🗑️ Temp: {temp_result.get('freed', 'N/A')}",
            "action": "optimize",
            "details": results,
            "stats": stats
        }

    def clean_pc(self) -> Dict:
        """Deep clean PC"""
        return self.optimize_pc()

    def optimize(self) -> Dict:
        """Backward-compatible alias used by older API routes."""
        return self.optimize_pc()

    def clean_temp(self) -> Dict:
        """Public safe temp cleanup (never touches Downloads)."""
        result = self._clean_temp()
        return {
            "success": True,
            "action": "clean_temp",
            "freed": result.get("freed", "0 B"),
            "message": f"🧹 Temp cleaned: {result.get('freed', '0 B')}",
            "details": result,
        }

    def _clean_ram(self) -> Dict:
        """Clean RAM by clearing caches"""
        try:
            before = psutil.virtual_memory().available

            if self.is_windows:
                # Use RAMMap or internal cleanup
                subprocess.run("echo 1 > /proc/sys/vm/drop_caches", shell=True, capture_output=True)
            elif self.is_linux:
                subprocess.run("sync && echo 3 > /proc/sys/vm/drop_caches", shell=True, capture_output=True)

            after = psutil.virtual_memory().available
            freed = after - before

            return {
                "action": "ram_clean",
                "freed": self._human_size(max(0, freed)),
                "before": self._human_size(before),
                "after": self._human_size(after)
            }
        except Exception as e:
            return {"action": "ram_clean", "freed": "0 B", "error": str(e)}

    def _clean_disk(self) -> Dict:
        """Clean disk junk"""
        try:
            total_freed = 0

            # Windows temp locations. Downloads is intentionally excluded:
            # deleting a user's Downloads is data loss, not cleanup.
            temp_paths = [
                os.environ.get('TEMP', ''),
                os.environ.get('TMP', ''),
                os.path.expanduser('~\\AppData\\Local\\Temp') if self.is_windows else '/tmp',
            ]

            for path in temp_paths:
                if path and os.path.exists(path):
                    try:
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            try:
                                if os.path.isfile(item_path):
                                    size = os.path.getsize(item_path)
                                    os.remove(item_path)
                                    total_freed += size
                                elif os.path.isdir(item_path):
                                    size = self._get_folder_size(item_path)
                                    shutil.rmtree(item_path)
                                    total_freed += size
                            except:
                                pass
                    except:
                        pass

            return {
                "action": "disk_clean",
                "freed": self._human_size(total_freed)
            }
        except Exception as e:
            return {"action": "disk_clean", "freed": "0 B", "error": str(e)}

    def _clean_temp(self) -> Dict:
        """Clean temporary files"""
        return self._clean_disk()

    def _empty_recycle_bin(self) -> Dict:
        """Empty recycle bin/trash"""
        try:
            if self.is_windows:
                try:
                    winshell = __import__('winshell')
                    winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
                except Exception:
                    # Fallback: use PowerShell clear-recyclebin if winshell is not available
                    try:
                        subprocess.run('PowerShell -Command "Clear-RecycleBin -Force -Confirm:$false"', shell=True)
                    except Exception:
                        pass
            elif self.is_linux:
                trash_paths = [
                    os.path.expanduser('~/.local/share/Trash/files'),
                    os.path.expanduser('~/.local/share/Trash/info')
                ]
                for path in trash_paths:
                    if os.path.exists(path):
                        shutil.rmtree(path)
                        os.makedirs(path)
            elif self.is_mac:
                subprocess.run("osascript -e 'tell application \"Finder\" to empty trash'", shell=True)

            return {"action": "empty_bin", "freed": "Cleaned"}
        except Exception as e:
            return {"action": "empty_bin", "freed": "0 B", "error": str(e)}

    # ========== BATTERY ==========

    def battery_status(self) -> Dict:
        """Get battery status"""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"success": False, "message": "🔌 No battery detected (Desktop PC)"}

            percent = battery.percent
            is_plugged = battery.power_plugged
            time_left = battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None

            status_emoji = "🔌" if is_plugged else "🔋"
            status_text = "Charging" if is_plugged else "Discharging"

            # Color indicator
            if percent >= 80:
                color = "🟢"
            elif percent >= 50:
                color = "🟡"
            elif percent >= 20:
                color = "🟠"
            else:
                color = "🔴"

            time_str = ""
            if time_left and not is_plugged:
                hours = time_left // 3600
                mins = (time_left % 3600) // 60
                time_str = f"\n⏱️ Time remaining: {hours}h {mins}m"

            return {
                "success": True,
                "message": f"{color} {status_emoji} Battery: {percent}% ({status_text}){time_str}",
                "percent": percent,
                "is_plugged": is_plugged,
                "time_left": time_left,
                "action": "battery_status"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ Battery check failed: {str(e)}"}

    # ========== SYSTEM STATUS ==========

    def system_status(self) -> Dict:
        """Get complete system status"""
        try:
            stats = self._get_system_stats()

            message = f"""📊 System Status ({self.system})

🖥️ CPU: {stats['cpu']['usage']}% ({stats['cpu']['cores']} cores)
🧠 RAM: {stats['ram']['used']} / {stats['ram']['total']} ({stats['ram']['percent']}%)
💾 Disk: {stats['disk']['used']} / {stats['disk']['total']} ({stats['disk']['percent']}%)
🌡️ Uptime: {stats['uptime']}"""

            # Add battery if laptop
            battery = psutil.sensors_battery()
            if battery:
                message += f"\n🔋 Battery: {battery.percent}%"

            return {
                "success": True,
                "message": message,
                "stats": stats,
                "action": "system_status"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ Status check failed: {str(e)}"}

    def _get_system_stats(self) -> Dict:
        """Get raw system statistics"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_cores = psutil.cpu_count()

        # RAM
        ram = psutil.virtual_memory()

        # Disk
        disk = psutil.disk_usage('/')

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.now().timestamp() - boot_time
        uptime_str = self._format_uptime(uptime_seconds)

        return {
            "cpu": {
                "usage": cpu_percent,
                "cores": cpu_cores,
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "ram": {
                "total": self._human_size(ram.total),
                "used": self._human_size(ram.used),
                "available": self._human_size(ram.available),
                "percent": ram.percent
            },
            "disk": {
                "total": self._human_size(disk.total),
                "used": self._human_size(disk.used),
                "free": self._human_size(disk.free),
                "percent": round(disk.used / disk.total * 100, 1)
            },
            "uptime": uptime_str,
            "platform": self.system
        }

    # ========== NETWORK ==========

    def wifi_status(self) -> Dict:
        """Get WiFi status"""
        try:
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            wifi_found = False
            wifi_name = "Unknown"

            for name, addrs in interfaces.items():
                if any(x in name.lower() for x in ['wi-fi', 'wifi', 'wlan', 'wl']):
                    wifi_found = True
                    wifi_name = name
                    break

            if not wifi_found:
                return {"success": True, "message": "📡 WiFi: Not connected or no WiFi adapter", "connected": False}

            # Try to get SSID
            ssid = "Unknown"
            try:
                if self.is_windows:
                    result = subprocess.run("netsh wlan show interfaces", shell=True, capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if 'SSID' in line and 'BSSID' not in line:
                            ssid = line.split(':')[-1].strip()
                            break
                elif self.is_linux:
                    result = subprocess.run("iwgetid -r", shell=True, capture_output=True, text=True)
                    ssid = result.stdout.strip() or "Unknown"
            except:
                pass

            return {
                "success": True,
                "message": f"📡 WiFi: {ssid} (via {wifi_name})",
                "connected": True,
                "ssid": ssid,
                "interface": wifi_name
            }
        except Exception as e:
            return {"success": False, "message": f"❌ WiFi check failed: {str(e)}"}

    def wifi_toggle(self, enable: bool = True) -> Dict:
        """Toggle WiFi on/off"""
        try:
            action = "enable" if enable else "disable"
            if self.is_windows:
                subprocess.run(f'netsh interface set interface "Wi-Fi" {action}', shell=True)
            elif self.is_linux:
                subprocess.run(f"nmcli radio wifi {'on' if enable else 'off'}", shell=True)
            elif self.is_mac:
                subprocess.run(f"networksetup -setairportpower en0 {'on' if enable else 'off'}", shell=True)

            return {
                "success": True,
                "message": f"📡 WiFi {'enabled' if enable else 'disabled'}"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ WiFi toggle failed: {str(e)}"}

    def bluetooth_status(self) -> Dict:
        """Get Bluetooth status"""
        try:
            # Check if Bluetooth is available
            if self.is_windows:
                result = subprocess.run("powershell Get-PnpDevice -Class Bluetooth", shell=True, capture_output=True, text=True)
                has_bluetooth = "Bluetooth" in result.stdout
            elif self.is_linux:
                result = subprocess.run("hciconfig", shell=True, capture_output=True, text=True)
                has_bluetooth = result.returncode == 0
            else:
                has_bluetooth = False

            if not has_bluetooth:
                return {"success": True, "message": "🔵 Bluetooth: No adapter found", "available": False}

            return {
                "success": True,
                "message": "🔵 Bluetooth: Available",
                "available": True
            }
        except Exception as e:
            return {"success": False, "message": f"❌ Bluetooth check failed: {str(e)}"}

    # ========== PROCESS MANAGEMENT ==========

    def process_manager(self, action: str = "list", process_name: str = "") -> Dict:
        """Manage running processes"""
        try:
            if action == "list":
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        info = proc.info
                        if info['cpu_percent'] > 0.1 or info['memory_percent'] > 0.1:
                            processes.append(info)
                    except:
                        pass

                # Sort by CPU usage
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
                top = processes[:10]

                msg = "🔥 Top Processes:\n"
                for p in top:
                    msg += f"  {p['name']} (PID: {p['pid']}) - CPU: {p['cpu_percent']:.1f}%\n"

                return {"success": True, "message": msg, "processes": top}

            elif action == "kill" and process_name:
                killed = []
                for proc in psutil.process_iter(['pid', 'name']):
                    if process_name.lower() in proc.info['name'].lower():
                        try:
                            p = psutil.Process(proc.info['pid'])
                            p.terminate()
                            killed.append(proc.info['name'])
                        except:
                            pass

                return {
                    "success": True,
                    "message": f"🛑 Killed: {', '.join(killed)}" if killed else "No matching process found"
                }

            return {"success": False, "message": "Unknown process action"}
        except Exception as e:
            return {"success": False, "message": f"❌ Process manager error: {str(e)}"}

    # ========== STARTUP APPS ==========

    def startup_apps(self) -> Dict:
        """List startup applications"""
        try:
            if self.is_windows:
                import winreg
                startup_paths = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                ]
                apps = []
                for hkey, path in startup_paths:
                    try:
                        with winreg.OpenKey(hkey, path) as key:
                            i = 0
                            while True:
                                try:
                                    name, value, _ = winreg.EnumValue(key, i)
                                    apps.append({"name": name, "path": value})
                                    i += 1
                                except OSError:
                                    break
                    except:
                        pass

                msg = f"🚀 Startup Apps ({len(apps)}):\n"
                for app in apps[:10]:
                    msg += f"  • {app['name']}\n"

                return {"success": True, "message": msg, "apps": apps}
            else:
                return {"success": True, "message": "🚀 Startup apps: Use system settings on Linux/Mac"}
        except Exception as e:
            return {"success": False, "message": f"❌ Startup check failed: {str(e)}"}

    # ========== MAIN HANDLER ==========

    def handle(self, intent: str, entities: Dict) -> Dict:
        """Route to appropriate PC action"""
        intent_lower = intent.lower()

        # System control
        if intent_lower in ["pc_shutdown", "shutdown"]:
            delay = int(entities.get("delay", 0))
            return self.shutdown(delay)

        elif intent_lower in ["pc_restart", "restart"]:
            delay = int(entities.get("delay", 0))
            return self.restart(delay)

        elif intent_lower in ["pc_lock", "lock", "security_lock"]:
            return self.lock()

        elif intent_lower in ["pc_sleep", "sleep"]:
            return self.sleep()

        # Optimization
        elif intent_lower in ["pc_optimize", "optimize_pc", "optimize"]:
            return self.optimize_pc()

        elif intent_lower in ["pc_clean", "clean_pc", "clean"]:
            return self.clean_pc()

        # Status
        elif intent_lower in ["pc_battery", "battery"]:
            return self.battery_status()

        elif intent_lower in ["pc_status", "system_status", "status"]:
            return self.system_status()

        # Network
        elif intent_lower in ["pc_wifi", "wifi"]:
            return self.wifi_status()

        elif intent_lower in ["pc_bluetooth", "bluetooth"]:
            return self.bluetooth_status()

        # Process management
        elif intent_lower in ["process_manager", "processes", "task_manager"]:
            return self.process_manager()

        elif intent_lower in ["startup_apps", "startup"]:
            return self.startup_apps()

        # Default: system status
        return self.system_status()

    # ========== HELPERS ==========

    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _get_folder_size(self, path: str) -> int:
        """Get folder size in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime string"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        mins = int((seconds % 3600) // 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")

        return " ".join(parts) if parts else "Just started"


# Singleton
pc_agent = PCAgent()