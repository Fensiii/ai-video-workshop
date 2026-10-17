// Usage: node render.js [out.mp4] [--preview t1,t2,...]
//        node render.js seg.mp4 --frames from,to   (video-only segment, used by render.sh)
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs"), path = require("path");

const FPS = 30;
const args = process.argv.slice(2);
const previewIdx = args.indexOf("--preview");
const framesIdx = args.indexOf("--frames");
const tl = JSON.parse(fs.readFileSync(path.join(__dirname, "build/timeline.json"), "utf8"));

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto("file://" + path.join(__dirname, "index.html"));
  await page.evaluate((t) => window.setup(t), tl);
  await page.evaluate(() => document.fonts.ready);

  if (previewIdx >= 0) {
    for (const t of args[previewIdx + 1].split(",").map(Number)) {
      await page.evaluate((t) => window.renderAt(t), t);
      await page.screenshot({ path: path.join(__dirname, `build/preview_${t}.png`) });
    }
    await browser.close();
    return;
  }

  const out = args[0] || path.join(__dirname, "build/tesla-evolution.mp4");
  const segment = framesIdx >= 0;
  const audio = segment ? ["-an"] : ["-i", path.join(__dirname, "build/narration.wav"),
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest"];
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error",
    "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-", ...audio,
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });

  const total = Math.ceil(tl.duration * FPS);
  const [from, to] = segment ? args[framesIdx + 1].split(",").map(Number) : [0, total];
  for (let f = from; f < Math.min(to, total); f++) {
    await page.evaluate((t) => window.renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (f % 300 === 0) console.log(`frame ${f}/${to}`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
  await browser.close();
  console.log("wrote", out);
})();
