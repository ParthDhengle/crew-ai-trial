import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
// Get __dirname equivalent for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
let mainWindow; // Full chat window
let miniWindow; // Mini widget window
let mainLoaded = false;
let miniLoaded = false;
let expandThrottle = 0; // Debounce IPC

console.log('MAIN: Starting main process...');

function createMainWindow() {
  console.log('MAIN: Creating main window...');
 
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: true,
    resizable: true,
    show: false, // Don't show initially
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    backgroundColor: 'transparent',
  });
  // FIXED: Use consistent port 5173 (matches vite.config.ts)
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('MAIN: Main window loaded successfully');
    mainLoaded = true;
   
    // Apply theme
    mainWindow.webContents.insertCSS(`
      :root {
        --nova-bg: #05060A;
        --nova-cyan: #00B7C7;
        --nova-accent: #007F8A;
        --nova-text: #E6F7F8;
        --nova-muted: #1a2930;
      }
    `);
  });
  mainWindow.webContents.on('did-fail-load', (e, code, desc) => {
    console.error('MAIN: Main load failed:', code, desc);
  });
  // NEW: Crash listener
  mainWindow.webContents.on('crashed', (e, killed) => {
    console.error('MAIN: Renderer crashed:', killed ? 'killed' : 'crashed');
  });
  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createMiniWindow() {
  console.log('MAIN: Creating mini window...');
 
  miniWindow = new BrowserWindow({
    width: 280,
    height: 400,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: true,
    minWidth: 200,
    minHeight: 300,
    maxWidth: 400,
    maxHeight: 600,
    show: false, // Don't show initially
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    backgroundColor: 'transparent',
  });
  // FIXED: DevTools only in dev, consistent port 5173
  if (process.env.NODE_ENV === 'development') {
    miniWindow.loadURL('http://localhost:5173?mini=true');
    miniWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    miniWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    // Set mini mode for production
    miniWindow.webContents.executeJavaScript(`
      window.isMiniMode = true;
      document.documentElement.setAttribute('data-mini', 'true');
    `);
  }
  miniWindow.webContents.on('did-finish-load', () => {
    console.log('MAIN: Mini window loaded successfully');
    miniLoaded = true;
   
    // Show mini window once loaded
    miniWindow.show();
    miniWindow.focus();
  });
  miniWindow.webContents.on('did-fail-load', (e, code, desc) => {
    console.error('MAIN: Mini load failed:', code, desc);
  });
  // NEW: Crash listener
  miniWindow.webContents.on('crashed', (e, killed) => {
    console.error('MAIN: Mini renderer crashed:', killed ? 'killed' : 'crashed');
  });
  // Handle window close
  miniWindow.on('closed', () => {
    miniWindow = null;
  });
  // Auto-minimize when focus is lost
  miniWindow.on('blur', () => {
    if (mainWindow && !mainWindow.isVisible()) {
      miniWindow.webContents.send('minimize-widget');
    }
  });
}

// FIXED: IPC with debounce (prevent loop)
ipcMain.handle('requestExpand', async () => {
  const now = Date.now();
  if (now - expandThrottle < 1000) { // 1s throttle
    console.log('MAIN: requestExpand throttled');
    return { success: false, error: 'Throttled' };
  }
  expandThrottle = now;
  console.log('MAIN: IPC requestExpand received!');
 
  try {
    // Hide mini window first
    if (miniWindow && miniWindow.isVisible()) {
      miniWindow.hide();
      console.log('MAIN: Mini window hidden');
    }
    // Wait for main window to be loaded if not ready
    if (!mainLoaded) {
      console.log('MAIN: Waiting for main to load...');
      await new Promise(resolve => {
        const checkLoaded = () => {
          if (mainLoaded) {
            resolve(undefined);
          } else {
            setTimeout(checkLoaded, 100);
          }
        };
        checkLoaded();
      });
    }
    // Show and focus main window
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
      mainWindow.setAlwaysOnTop(false);
     
      // Force reload in development to ensure fresh content
      if (process.env.NODE_ENV === 'development') {
        mainWindow.webContents.reloadIgnoringCache();
        console.log('MAIN: Main window reloaded (dev mode)');
      }
     
      console.log('MAIN: Main window shown and focused!');
    }
    return { success: true };
  } catch (error) {
    console.error('MAIN: Error in requestExpand:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('requestMinimize', async () => {
  console.log('MAIN: IPC requestMinimize received!');
 
  try {
    // Hide main window
    if (mainWindow && mainWindow.isVisible()) {
      mainWindow.hide();
      console.log('MAIN: Main window hidden');
    }
    // Wait for mini window to be loaded if not ready
    if (!miniLoaded) {
      console.log('MAIN: Waiting for mini window to load...');
      await new Promise(resolve => {
        const checkLoaded = () => {
          if (miniLoaded) {
            resolve(undefined);
          } else {
            setTimeout(checkLoaded, 100);
          }
        };
        checkLoaded();
      });
    }
    // Show mini window
    if (miniWindow) {
      miniWindow.show();
      miniWindow.focus();
      miniWindow.setAlwaysOnTop(true);
      console.log('MAIN: Mini window shown');
    }
    return { success: true };
  } catch (error) {
    console.error('MAIN: Error in requestMinimize:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('setAlwaysOnTop', (event, flag) => {
  if (mainWindow) mainWindow.setAlwaysOnTop(flag);
  if (miniWindow) miniWindow.setAlwaysOnTop(flag);
});

// Window control handlers
ipcMain.on("window:minimize", () => {
  const focused = BrowserWindow.getFocusedWindow();
  if (focused) {
    focused.minimize();
  }
});
ipcMain.on("window:maximize", () => {
  const focused = BrowserWindow.getFocusedWindow();
  if (focused) {
    if (focused.isMaximized()) {
      focused.unmaximize();
    } else {
      focused.maximize();
    }
  }
});
ipcMain.on("window:close", () => {
  // Close the focused window, or quit app if it's the last one
  const focused = BrowserWindow.getFocusedWindow();
  if (focused) {
    focused.close();
  } else {
    app.quit();
  }
});
// NEW: Handle mini window close specifically
ipcMain.on("mini:close", () => {
  if (miniWindow) {
    miniWindow.close();
  }
  // If mini closes and main isn't visible, quit the app
  if (!mainWindow || !mainWindow.isVisible()) {
    app.quit();
  }
});

app.whenReady().then(() => {
  console.log('MAIN: App ready—creating windows');
  createMainWindow();
  createMiniWindow();
 
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
      createMiniWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Prevent app from quitting when all windows are closed on macOS
app.on('before-quit', () => {
  console.log('MAIN: App is quitting...');
});