// src/sensors/SensorCapture.js
export async function startSensors(onData) {
  // Webcam stream
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  
  // Send frames to backend for eye tracking
  const video = document.createElement('video');
  video.srcObject = stream;
  video.play();
  
  const canvas = document.createElement('canvas');
  canvas.width = 320; canvas.height = 240;
  const ctx = canvas.getContext('2d');
  
  // Keyboard tracker
  let keyCount = 0, errorCount = 0, lastKeyTime = Date.now();
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') errorCount++;
    keyCount++;
  });

  // Mouse tracker
  let mousePositions = [];
  document.addEventListener('mousemove', (e) => {
    mousePositions.push({ x: e.clientX, y: e.clientY, t: Date.now() });
    if (mousePositions.length > 10) mousePositions.shift();
  });

  // Send data every 1.5s
  setInterval(() => {
    ctx.drawImage(video, 0, 0, 320, 240);
    const frameData = canvas.toDataURL('image/jpeg', 0.6); // base64 frame
    
    const vel = calcMouseVelocity(mousePositions);
    const wpm = calcWPM(keyCount, lastKeyTime);
    
    onData({ frame: frameData, mouse_vel: vel, wpm, error_count: errorCount });
    keyCount = 0; errorCount = 0; lastKeyTime = Date.now();
  }, 1500);
}

function calcMouseVelocity(positions) {
  if (positions.length < 2) return 0;
  const a = positions[0], b = positions[positions.length - 1];
  const dist = Math.hypot(b.x - a.x, b.y - a.y);
  const time = (b.t - a.t) / 1000;
  return time > 0 ? dist / time : 0;
}

function calcWPM(keys, lastTime) {
  const minutes = (Date.now() - lastTime) / 60000;
  return minutes > 0 ? (keys / 5) / minutes : 0;
}