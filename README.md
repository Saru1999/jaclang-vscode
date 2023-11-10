[![Release](https://github.com/Jaseci-Labs/jaclang-vscode/actions/workflows/release.yml/badge.svg)](https://github.com/Jaseci-Labs/jaclang-vscode/actions/workflows/release.yml) [![Run Tests](https://github.com/Jaseci-Labs/jaclang-vscode/actions/workflows/ls_tests.yml/badge.svg)](https://github.com/Jaseci-Labs/jaclang-vscode/actions/workflows/ls_tests.yml)

# Jaclang Language Extension for VScode
The Jaclang Language Extension for VScode is an extension that provides basic Language Server Protocol (LSP) functionalities for the Jaclang programming language. Jaclang is a programming language developed by Jaseci-Labs, and it is designed to be a versatile and powerful language for building complex systems.

The extension provides features such as syntax highlighting, error diagnostics, auto-completion, and file handling. It also includes commands for restarting the server, running tests, running files, and clearing the cache.

The extension uses pygls as its language server, which is responsible for providing the LSP functionalities. The language server is bundled with the extension, but it can also be loaded from the environment if the user chooses to do so.

Overall, the Jaclang Language Extension for VScode is a useful tool for developers who are working with the Jaclang programming language, as it provides essential functionalities for developing and debugging Jaclang code.

## Features


| Feature | LSP Methods | Status | Remarks |
| ------- | ---------- | ------ | ------- |
| Auto-Completion | "textDocument/completion" | ✅ | 
| | "textDocument/inlineCompletion" | 🚧 |
| Snippets | "textDocument/completion" | ✅ |
| Syntax Highlighting | General Syntax Highlighting | ✅ |
| | Python Block Syntax Highlighting | 🚧 |
| Hover | "textDocument/hover" | ✅ |
| Definition | "textDocument/definition"| ✅ |
| Error Diagnostics | "textDocument/diagnostic" | ✅ |
| Auto-Formatting | "textDocument/formatting" | ✅ |
| | "textDocument/rangeFormatting" | 🚧 |
| | "textDocument/rangesFormatting" | 🚧 |
| File Handling | "textDocument/didOpen" | ✅ |
| | "textDocument/didChange" | ✅ |
| | "textDocument/didSave" | ✅ |
| | "textDocument/didClose" | ✅ |
| File Operations Handling | "workspace/didCreateFiles" | ✅ |
| | "workspace/didRenameFiles" | ✅ |
| | "workspace/didDeleteFiles" | ✅ |
| General Methods | "textDocument/documentSymbol" | ✅ |

## Commands

| Command                | Description                         | Status |
| ---------------------- | ----------------------------------- | ------ |
| Jaseci: Restart Server | Force re-start the language server. |  ✅   |
| Jaseci: Run Tests      | Run the Tests in the Workspace  |  🚧   |
| Jaseci: Run File       | Run the File in the Workspace  |  🚧   |
| Jaseci: Clear Cache    | Clear the Cache  |  🚧   |


## Settings

| Settings | Default | Description |
| -------- | ------- | ----------- |
| jaseci.severity | `{ "error": "Error", "note": "Information" }` | Controls mapping of severity from `jaseci` to VS Code severity when displaying in the problems window. You can override specific `jac` error codes `{ "error": "Error", "note": "Information", "name-defined": "Warning" }` |
| jaseci.interpreter | `[]` | Path to a Python interpreter to use to run the Jaseci language server. When set to `[]`, the interpreter for the workspace is obtained from `ms-python.python` extension. If set to some path, that path takes precedence, and the Python extension is not queried for the interpreter. |
| jaseci.importStrategy | `useBundled` | Setting to choose where to load `jaclang` from. `useBundled` picks jaclang bundled with the extension. `fromEnvironment` uses `jaclang` available in the environment. |
| jaseci.showNotifications | `off` | Setting to control when a notification is shown. |
| jaseci.reportingScope | `file` | (experimental) Setting to control if problems are reported for files open in the editor (`file`) or for the entire workspace (`workspace`). |
| jaseci.showWarnings | ` false` | Setting to control if warnings are shown in the file/workspace |

## Contributing

### Pre-requisites

-   [Node.js](https://nodejs.org/en/)
-   [VS Code](https://code.visualstudio.com/)
-   [Python](https://www.python.org/)(3.11)
    -   [Conda](https://docs.conda.io/en/latest/) (optional) `conda create -n vscode-jaseci python=3.11 -y`

### Setup

Install Nox (Make sure to have python 3.11)

```bash
pip install nox
```

Install Dependencies (both Python and Node.js)

```bash
nox --session setup
```

You are ready to run the extension in a development environment.

### Build

To build the `.vsix` (VSCode Extension file)

```bash
npm run vsce-package
```

### Running Tests

To run language server tests

```bash
pytest
```

Then you can install the extension on your VSCode using this https://code.visualstudio.com/docs/editor/extension-marketplace

## Logging

From the command palette (View > Command Palette ...), run the `Developer: Set Log Level...` command. From the quick pick menu, select `Jaseci Language Server` extension from the `Extension logs` group. Then select the log level you want to set.
