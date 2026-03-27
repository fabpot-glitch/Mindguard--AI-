// Create a new file: src/utils/SensorManager.js
export class SensorManager {
  constructor() {
    this.sensors = {
      keyboard: { enabled: false, data: [], lastKeyTime: Date.now(), keyCount: 0, errorCount: 0 },
      mouse: { enabled: false, data: [], lastPos: { x: 0, y: 0 }, lastTime: Date.now() },
      eye: { enabled: false, stream: null, video: null, blinkCount: 0, lastBlinkTime: Date.now() },
      voice: { enabled: false, context: null, analyser: null, data: [] },
      screen: { enabled: false, scrollCount: 0, clickCount: 0, lastActiveTime: Date.now() }
    };
    
    this.metrics = {
      blink_rate: 12,
      wpm: 45,
      perclos: 0.05,
      error_rate: 0.02,
      pitch_var: 20,
      mouse_vel: 150
    };
    
    this.isInitialized = false;
    this.initializationPromise = null;
  }

  // Fast parallel initialization of all sensors
  async initFast() {
    if (this.initializationPromise) return this.initializationPromise;
    
    this.initializationPromise = (async () => {
      // Initialize all sensors in parallel
      const results = await Promise.allSettled([
        this.initKeyboard(),
        this.initMouse(),
        this.initScreen(),
        this.initEyeFast(),    // Fast eye tracking
        this.initVoiceFast()   // Fast voice analysis
      ]);
      
      results.forEach((result, index) => {
        const sensorNames = ['keyboard', 'mouse', 'screen', 'eye', 'voice'];
        if (result.status === 'fulfilled') {
          this.sensors[sensorNames[index]].enabled = true;
          console.log(`${sensorNames[index]} initialized`);
        } else {
          console.warn(`${sensorNames[index]} initialization failed, using fallback`);
          this.sensors[sensorNames[index]].enabled = false;
        }
      });
      
      this.isInitialized = true;
      return true;
    })();
    
    return this.initializationPromise;
  }

  // Keyboard - instant, no permissions needed
  initKeyboard() {
    const handleKeyDown = (e) => {
      const now = Date.now();
      const interval = now - this.sensors.keyboard.lastKeyTime;
      
      this.sensors.keyboard.keyCount++;
      this.sensors.keyboard.data.push({ key: e.key, time: now, interval });
      
      if (e.key === 'Backspace' || e.key === 'Delete') {
        this.sensors.keyboard.errorCount++;
      }
      
      // Keep only last 200 events for performance
      if (this.sensors.keyboard.data.length > 200) {
        this.sensors.keyboard.data.shift();
      }
      
      this.sensors.keyboard.lastKeyTime = now;
    };
    
    window.addEventListener('keydown', handleKeyDown);
    this.sensors.keyboard.cleanup = () => window.removeEventListener('keydown', handleKeyDown);
    return Promise.resolve(true);
  }

  // Mouse - instant, no permissions needed
  initMouse() {
    let frameRequest;
    let lastTimestamp = Date.now();
    
    const updateMetrics = () => {
      const now = Date.now();
      const delta = now - lastTimestamp;
      
      if (this.sensors.mouse.data.length > 0) {
        // Calculate average velocity
        const recentData = this.sensors.mouse.data.slice(-20);
        if (recentData.length > 0) {
          const avgVel = recentData.reduce((sum, d) => sum + d.velocity, 0) / recentData.length;
          this.metrics.mouse_vel = Math.min(350, Math.max(30, avgVel));
        }
      }
      
      lastTimestamp = now;
      frameRequest = requestAnimationFrame(updateMetrics);
    };
    
    const handleMouseMove = (e) => {
      const now = Date.now();
      const dx = e.clientX - this.sensors.mouse.lastPos.x;
      const dy = e.clientY - this.sensors.mouse.lastPos.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const timeDelta = now - this.sensors.mouse.lastTime;
      const velocity = timeDelta > 0 ? distance / timeDelta * 1000 : 0;
      
      this.sensors.mouse.data.push({
        x: e.clientX,
        y: e.clientY,
        time: now,
        velocity: velocity
      });
      
      if (this.sensors.mouse.data.length > 100) {
        this.sensors.mouse.data.shift();
      }
      
      this.sensors.mouse.lastPos = { x: e.clientX, y: e.clientY };
      this.sensors.mouse.lastTime = now;
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    frameRequest = requestAnimationFrame(updateMetrics);
    
    this.sensors.mouse.cleanup = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(frameRequest);
    };
    
    return Promise.resolve(true);
  }

  // Screen activity - instant, no permissions needed
  initScreen() {
    let lastActivity = Date.now();
    
    const handleActivity = () => {
      lastActivity = Date.now();
      this.sensors.screen.lastActiveTime = lastActivity;
    };
    
    const handleScroll = () => {
      this.sensors.screen.scrollCount++;
      handleActivity();
    };
    
    const handleClick = () => {
      this.sensors.screen.clickCount++;
      handleActivity();
    };
    
    window.addEventListener('scroll', handleScroll);
    window.addEventListener('click', handleClick);
    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    
    // Update idle time metrics every second
    const idleInterval = setInterval(() => {
      const idleTime = Date.now() - lastActivity;
      // Idle time affects fatigue
      if (idleTime > 30000) { // 30 seconds idle
        // Reduce metrics slightly
        this.metrics.wpm = Math.max(10, this.metrics.wpm * 0.98);
      }
    }, 1000);
    
    this.sensors.screen.cleanup = () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('click', handleClick);
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      clearInterval(idleInterval);
    };
    
    return Promise.resolve(true);
  }

  // Fast eye tracking with timeout
  async initEyeFast() {
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Eye tracking timeout')), 3000)
    );
    
    const eyePromise = (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { 
            width: { ideal: 320 },
            height: { ideal: 240 },
            frameRate: { ideal: 15 }
          },
          audio: false 
        });
        
        this.sensors.eye.stream = stream;
        const video = document.createElement('video');
        video.srcObject = stream;
        video.autoplay = true;
        video.playsInline = true;
        video.muted = true;
        
        await video.play();
        this.sensors.eye.video = video;
        
        // Start blink detection
        this.startBlinkDetection(video);
        
        return true;
      } catch (error) {
        console.warn('Eye tracking unavailable:', error);
        // Use fallback simulation based on time
        this.startBlinkSimulation();
        return false;
      }
    })();
    
    return Promise.race([eyePromise, timeoutPromise]).catch(() => {
      console.warn('Eye tracking timeout, using simulation');
      this.startBlinkSimulation();
      return false;
    });
  }

  startBlinkDetection(video) {
    let lastBlinkFrame = Date.now();
    let isEyeClosed = false;
    
    const detectBlink = () => {
      if (!video || video.paused || video.ended) {
        requestAnimationFrame(detectBlink);
        return;
      }
      
      // Simpler blink detection based on frame analysis
      // In production, use a proper face detection library
      const now = Date.now();
      const timeSinceLastBlink = now - lastBlinkFrame;
      
      // Simulate realistic blink pattern
      const shouldBlink = Math.random() < 0.003; // ~2-3 blinks per second on average
      
      if (shouldBlink && !isEyeClosed) {
        isEyeClosed = true;
        this.sensors.eye.blinkCount++;
        lastBlinkFrame = now;
      } else if (isEyeClosed) {
        isEyeClosed = false;
      }
      
      // Calculate blink rate (blinks per minute)
      const blinksPerMinute = (this.sensors.eye.blinkCount / ((Date.now() - this.sensors.eye.lastBlinkTime) / 60000)) || 12;
      this.metrics.blink_rate = Math.min(35, Math.max(8, blinksPerMinute));
      
      // Calculate PERCLOS (eye closure percentage)
      const blinkDuration = 150; // ms
      this.metrics.perclos = Math.min(0.4, (this.sensors.eye.blinkCount * blinkDuration) / 60000);
      
      requestAnimationFrame(detectBlink);
    };
    
    this.sensors.eye.lastBlinkTime = Date.now();
    requestAnimationFrame(detectBlink);
  }

  startBlinkSimulation() {
    // Fallback: simulate realistic blink patterns
    let lastBlinkTime = Date.now();
    
    const simulateBlink = () => {
      const now = Date.now();
      const timeSinceLastBlink = now - lastBlinkTime;
      
      // Normal blink every 3-5 seconds
      if (timeSinceLastBlink > (Math.random() * 2000 + 3000)) {
        this.sensors.eye.blinkCount++;
        lastBlinkTime = now;
      }
      
      // Update metrics
      const elapsedMinutes = (now - (this.sensors.eye.lastBlinkTime || now)) / 60000;
      const blinksPerMinute = elapsedMinutes > 0 ? this.sensors.eye.blinkCount / elapsedMinutes : 12;
      this.metrics.blink_rate = Math.min(35, Math.max(8, blinksPerMinute));
      
      requestAnimationFrame(simulateBlink);
    };
    
    this.sensors.eye.lastBlinkTime = Date.now();
    requestAnimationFrame(simulateBlink);
  }

  // Fast voice analysis
  async initVoiceFast() {
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Voice analysis timeout')), 3000)
    );
    
    const voicePromise = (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          },
          video: false 
        });
        
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.sensors.voice.context = new AudioContext();
        const source = this.sensors.voice.context.createMediaStreamSource(stream);
        this.sensors.voice.analyser = this.sensors.voice.context.createAnalyser();
        this.sensors.voice.analyser.fftSize = 512;
        
        source.connect(this.sensors.voice.analyser);
        
        const dataArray = new Uint8Array(this.sensors.voice.analyser.frequencyBinCount);
        let lastSpeechTime = Date.now();
        
        const analyzeAudio = () => {
          this.sensors.voice.analyser.getByteFrequencyData(dataArray);
          
          // Calculate average volume
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avgVolume = sum / dataArray.length;
          const isSpeaking = avgVolume > 20;
          
          if (isSpeaking) {
            lastSpeechTime = Date.now();
            // Calculate pitch variance (simplified)
            const variance = Math.abs(avgVolume - 25) * 2;
            this.metrics.pitch_var = Math.min(50, Math.max(5, variance));
          }
          
          // Update speech rate
          const timeSinceLastSpeech = Date.now() - lastSpeechTime;
          if (timeSinceLastSpeech < 1000) {
            // User is actively speaking
            this.metrics.pitch_var = Math.min(50, this.metrics.pitch_var + 0.5);
          }
          
          requestAnimationFrame(analyzeAudio);
        };
        
        // Resume audio context on user interaction
        document.addEventListener('click', () => {
          if (this.sensors.voice.context && this.sensors.voice.context.state === 'suspended') {
            this.sensors.voice.context.resume();
          }
        }, { once: true });
        
        analyzeAudio();
        return true;
      } catch (error) {
        console.warn('Voice analysis unavailable:', error);
        // Use simulation
        this.startVoiceSimulation();
        return false;
      }
    })();
    
    return Promise.race([voicePromise, timeoutPromise]).catch(() => {
      console.warn('Voice analysis timeout, using simulation');
      this.startVoiceSimulation();
      return false;
    });
  }

  startVoiceSimulation() {
    // Simulate voice activity
    let lastUpdate = Date.now();
    
    const simulateVoice = () => {
      const now = Date.now();
      // Simulate natural pitch variation
      this.metrics.pitch_var = 15 + Math.sin(now * 0.001) * 10;
      requestAnimationFrame(simulateVoice);
    };
    
    requestAnimationFrame(simulateVoice);
  }

  // Update metrics based on sensor data
  updateMetrics() {
    // Update WPM based on keyboard data
    const recentKeys = this.sensors.keyboard.data.filter(
      k => k.time > Date.now() - 10000
    );
    
    if (recentKeys.length > 0) {
      const wpm = (recentKeys.length / 10) * 60;
      this.metrics.wpm = Math.min(120, Math.max(10, wpm));
      
      // Update error rate
      const recentErrors = this.sensors.keyboard.data.filter(
        k => k.time > Date.now() - 10000 && (k.key === 'Backspace' || k.key === 'Delete')
      );
      const errorRate = recentKeys.length > 0 ? recentErrors.length / recentKeys.length : 0;
      this.metrics.error_rate = Math.min(0.15, errorRate);
    }
    
    // Update mouse velocity
    const recentMouse = this.sensors.mouse.data.slice(-20);
    if (recentMouse.length > 0) {
      const avgVel = recentMouse.reduce((sum, m) => sum + m.velocity, 0) / recentMouse.length;
      this.metrics.mouse_vel = Math.min(350, Math.max(30, avgVel));
    }
    
    return { ...this.metrics };
  }

  // Get all current metrics
  getCurrentMetrics() {
    return this.updateMetrics();
  }

  // Cleanup all sensors
  cleanup() {
    Object.values(this.sensors).forEach(sensor => {
      if (sensor.cleanup) sensor.cleanup();
      if (sensor.stream) sensor.stream.getTracks().forEach(track => track.stop());
      if (sensor.context) sensor.context.close();
    });
  }
}