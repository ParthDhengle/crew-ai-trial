const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow(selectedText = '') {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true
    }
  });

  win.loadFile('index.html');
  win.webContents.on('did-finish-load', () => {
    win.webContents.send('selected-text', selectedText);
  });

  return win;
}

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Parse args from second instance
    const selectedText = commandLine.find(arg => arg.startsWith('--selected-text='))?.split('=')[1] || '';
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
      mainWindow.webContents.send('selected-text', selectedText);
    }
  });

  app.whenReady().then(() => {
    // Parse initial args
    const selectedText = process.argv.find(arg => arg.startsWith('--selected-text='))?.split('=')[1] || '';
    mainWindow = createWindow(selectedText);
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
}