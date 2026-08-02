import {Config} from "@remotion/cli/config";
import {existsSync} from "node:fs";

/**
 * Remotion 全局配置
 *
 * 1. 浏览器：自动探测系统 Chrome / Edge / Chromium，找不到才让 Remotion 自己下载
 *    chrome-headless-shell（113MB，避免冷启动卡在下载）
 * 2. 并发：根据 CPU 物理核心数自动设置（默认 2）
 *
 * 覆盖方式：
 *   - 命令行：npx remotion still --browser-executable=...
 *   - 环境变量：REMOTION_BROWSER_EXECUTABLE=C:\Program Files\...
 */
const browserCandidates: string[] =
  process.platform === "win32"
    ? [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        process.env.LOCALAPPDATA
          ? `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`
          : "",
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      ]
    : process.platform === "darwin"
      ? [
          "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
      : [
          "/usr/bin/google-chrome",
          "/usr/bin/google-chrome-stable",
          "/usr/bin/chromium",
          "/usr/bin/chromium-browser",
          "/snap/bin/chromium",
        ];

for (const candidate of browserCandidates) {
  if (candidate && existsSync(candidate)) {
    Config.setBrowserExecutable(candidate);
    console.log(`[remotion.config] 使用本地浏览器：${candidate}`);
    break;
  }
}

if (!process.env.REMOTION_BROWSER_EXECUTABLE) {
  // 让 ffmpeg 渲染时输出位置可控
  Config.setConcurrency(Math.max(2, Math.floor((require("node:os").cpus()?.length ?? 4) / 2)));
}
