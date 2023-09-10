# Jaseci VSCode Extension
[![Language Server Tests](https://github.com/Jaseci-Labs/vscode/actions/workflows/server.yml/badge.svg)](https://github.com/Jaseci-Labs/vscode/actions/workflows/server.yml)
## Introduction

## Development

This section is for developers who want to contribute to the project. If you are just looking to use the extension, please refer to the following guide.

### Prerequisites

- [Node.js](https://nodejs.org/en/)
- [npm](https://www.npmjs.com/)

### Installation

1. Clone the repo

```sh
git clone https://github.com/Jaseci-Labs/vscode.git
```

2. Install NPM packages

```sh
npm install
```

3. Install Server Dependencies

```sh
pip install -r server/requirements.txt
# Installing Jaclang (Need to clone and install manually for now)
git clone https://github.com/Jaseci-Labs/jaclang.git
pip install -e jaclang
```

### Running the extension in Debugging mode

1. Build the extension (In Vscode)
Press `Ctrl + Shift + B (Windows/Linux)` or  `Cmd + Shift + B (MacOS)`

2. Run the extension in Debug mode
Press `Ctrl/Cmd + Shift + D`, select `Server + Client` from the dropdown menu and press 'Play' icon. This will open a new VSCode window with the extension loaded. Thats where you can test the extension.

> Note: If you make a change in the server code, you need to restart the debug session (both server and client) to see the changes.

### References

- [VSCode Extension API](https://code.visualstudio.com/api)
- [VSCode Extension API - Language Server](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide)
- [PyGLS - Python Language Server](https://pygls.readthedocs.io/en/latest/)
