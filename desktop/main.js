const { app, BrowserWindow, session, shell, globalShortcut, Menu, Tray, nativeImage, ipcMain, dialog } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');
const fs = require('fs');

const BACKEND_HOST = process.env.SERVER_HOST || '127.0.0.1';
const BACKEND_PORT = parseInt(process.env.SERVER_PORT || '8000', 10);
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const HEALTH_URL = `${BACKEND_URL}/health`;

let mainWindow = null;
let tray = null;
let pythonProcess = null;
let backendSpawnedByApp = false;
let isQuitting = false;

// Single-instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function findPythonExecutable() {
  const rootDir = path.resolve(__dirname, '..');
  const winVenv = path.join(rootDir, 'venv', 'Scripts', 'python.exe');
  const posixVenv = path.join(rootDir, 'venv', 'bin', 'python');

  if (process.platform === 'win32' && fs.existsSync(winVenv)) {
    return winVenv;
  }
  if (process.platform !== 'win32' && fs.existsSync(posixVenv)) {
    return posixVenv;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function checkBackendHealth(timeoutMs = 1000) {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, { timeout: timeoutMs }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend(maxWaitMs = 30000) {
  const startTime = Date.now();
  while (Date.now() - startTime < maxWaitMs) {
    const isHealthy = await checkBackendHealth(800);
    if (isHealthy) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function spawnPythonBackend() {
  const pyExe = findPythonExecutable();
  const rootDir = path.resolve(__dirname, '..');
  const scriptPath = path.join(rootDir, 'main.py');

  const args = [
    scriptPath,
    '--no-browser',
    '--host', BACKEND_HOST,
    '--port', String(BACKEND_PORT),
  ];

  console.log(`[*] Spawning Python backend: ${pyExe} ${args.join(' ')}`);

  pythonProcess = spawn(pyExe, args, {
    cwd: rootDir,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  backendSpawnedByApp = true;

  pythonProcess.stdout.on('data', (chunk) => {
    console.log(`[BACKEND STDOUT] ${chunk.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (chunk) => {
    console.error(`[BACKEND STDERR] ${chunk.toString().trim()}`);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[*] Backend process exited with code ${code}, signal ${signal}`);
    pythonProcess = null;
    if (!isQuitting && mainWindow && !mainWindow.isDestroyed()) {
      dialog.showErrorBox(
        'JARVIS Backend Disconnected',
        `The Python core service terminated unexpectedly (Code: ${code}).\nPlease restart the application.`
      );
    }
  });
}

function stopPythonBackend() {
  if (pythonProcess && backendSpawnedByApp) {
    console.log('[*] Terminating spawned Python backend...');
    try {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', String(pythonProcess.pid), '/f', '/t']);
      } else {
        pythonProcess.kill('SIGTERM');
      }
    } catch (e) {
      console.warn('Error killing python child:', e);
    }
    pythonProcess = null;
  }
}

function createMainWindow() {
  const windowOpts = {
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: 'JARVIS',
    frame: false,
    titleBarStyle: 'hidden',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  };

  if (process.platform === 'win32') {
    // Windows 11 Acrylic with titleBarOverlay
    windowOpts.backgroundMaterial = 'acrylic';
    windowOpts.titleBarOverlay = {
      color: 'rgba(0, 0, 0, 0)',
      symbolColor: '#3a3a3c',
      height: 52,
    };
    windowOpts.backgroundColor = '#f5f5f7';
  } else if (process.platform === 'darwin') {
    windowOpts.vibrancy = 'under-window';
    windowOpts.visualEffectState = 'active';
  } else {
    windowOpts.backgroundColor = '#f5f5f7';
  }

  mainWindow = new BrowserWindow(windowOpts);

  // Grant microphone permissions automatically for localhost / 127.0.0.1
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      callback(true);
    } else {
      callback(false);
    }
  });

  // Strict Navigation Security: prevent unexpected external navigation
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    const isLocal = navigationUrl.startsWith(BACKEND_URL) || navigationUrl.startsWith('http://localhost:8000');
    if (!isLocal) {
      event.preventDefault();
      shell.openExternal(navigationUrl);
    }
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      // Hide to system tray instead of destroying
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function setupTray() {
  try {
    const iconPath = path.join(__dirname, '..', 'ui', 'icon.svg');
    let trayIcon;
    if (fs.existsSync(iconPath)) {
      trayIcon = nativeImage.createFromPath(iconPath);
    }
    if (!trayIcon || trayIcon.isEmpty()) {
      // Fallback empty transparent 16x16 icon
      trayIcon = nativeImage.createEmpty();
    }

    tray = new Tray(trayIcon);
    tray.setToolTip('Project JARVIS Autonomous Assistant');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Show JARVIS',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      {
        label: 'Hide JARVIS',
        click: () => {
          if (mainWindow) mainWindow.hide();
        },
      },
      { type: 'separator' },
      {
        label: 'Quit JARVIS',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);
    tray.on('double-click', () => {
      if (mainWindow) {
        if (mainWindow.isVisible()) mainWindow.hide();
        else {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    });
  } catch (e) {
    console.warn('System tray setup notice:', e);
  }
}

// IPC Handlers for frameless window controls
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.on('open-external', (event, url) => {
  if (typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'))) {
    shell.openExternal(url);
  }
});

app.whenReady().then(async () => {
  // 1. Check if backend is already running
  const alreadyRunning = await checkBackendHealth(500);
  if (!alreadyRunning) {
    spawnPythonBackend();
  } else {
    console.log('[*] Detected running JARVIS backend on port 8000. Attaching...');
  }

  // 2. Poll until backend is healthy
  const ready = await waitForBackend(30000);
  if (!ready) {
    dialog.showErrorBox(
      'JARVIS Backend Failed to Start',
      `Could not establish connection to ${BACKEND_URL}/health within 30 seconds.\n` +
      'Please check your Python environment or logs.'
    );
    stopPythonBackend();
    app.quit();
    return;
  }

  // 3. Create Desktop Window and System Tray
  createMainWindow();
  setupTray();

  // 4. Register Global Shortcut to Summon JARVIS (Ctrl+Shift+Space / Cmd+Shift+Space)
  // Does not conflict with Ctrl+Alt+Q emergency switch
  const summonKey = 'CommandOrControl+Shift+Space';
  const registered = globalShortcut.register(summonKey, () => {
    if (mainWindow) {
      if (mainWindow.isVisible() && mainWindow.isFocused()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
  if (registered) {
    console.log(`[OK] Global summon shortcut registered: ${summonKey}`);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  globalShortcut.unregisterAll();
  stopPythonBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    isQuitting = true;
    app.quit();
  }
});

process.on('SIGINT', () => {
  isQuitting = true;
  stopPythonBackend();
  process.exit(0);
});

process.on('SIGTERM', () => {
  isQuitting = true;
  stopPythonBackend();
  process.exit(0);
});
