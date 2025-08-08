Project Structure:

- myproject/
  - package.json
  - index.js
  - frontend/
    - package.json
    - public/
      - index.html

Files Content:

1. myproject/package.json:
{
  "name": "myproject",
  "version": "1.0.0",
  "description": "My Web Application",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}

2. myproject/index.js:
const express = require('express');
const app = express();
const port = 3001;

app.use(express.json());

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});

3. myproject/frontend/package.json:
{
  "name": "myproject-frontend",
  "version": "1.0.0",
  "description": "Frontend for My Web Application",
  "main": "index.js",
  "scripts": {
    "start": "react-scripts start"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  }
}

4. myproject/frontend/public/index.html:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>

5. myproject/.gitignore:
node_modules/
.DS_Store