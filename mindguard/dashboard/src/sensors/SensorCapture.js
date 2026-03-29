import { WS_URL } from "../config";

export async function startSensors(onData) {
  const socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    console.log("✅ Connected to backend WebSocket");
  };

  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  
  const video = document.createElement('video');
  video.srcObject = stream;
  video.play();
  
  const canvas = document.createElement('canvas');
  canvas.width = 320; canvas.height = 240;
  const ctx = canvas.getContext('2d');

  let keyCount = 0, errorCount = 0, lastKeyTime = Date.now();

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') errorCount++;
    keyCount++;
  });

  let mousePositions = [];
  document.addEventListener('mousemove', (e) => {
    mousePositions.push({ x: e.clientX, y: e.clientY, t: Date.now() });
    if (mousePositions.length > 10) mousePositions.shift();
  });

  setInterval(() => {
    ctx.drawImage(video, 0, 0, 320, 240);
    const frameData = canvas.toDataURL('image/jpeg', 0.6);
    
    const vel = calcMouseVelocity(mousePositions);
    const wpm = calcWPM(keyCount, lastKeyTime);

    const payload = {
      frame: frameData,
      mouse_vel: vel,
      wpm,
      error_count: errorCount
    };

    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }

    onData(payload);

    keyCount = 0;
    errorCount = 0;
    lastKeyTime = Date.now();

  }, 1500);
}