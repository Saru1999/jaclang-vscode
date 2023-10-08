# Jaclang Language Extension for VScode

## Usage

## Features

1. Auto-Completion
2. Snippets
3. Syntax Highlighting
4. Hover
5. Definition
6. Error Diagnostics
7. Auto-Formatting

## Settings

| Settings                 | Default                                       | Description                                                                                                                                                                                                                                                                             |
| ------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| jaseci.severity          | `{ "error": "Error", "note": "Information" }` | Controls mapping of severity from `jaseci` to VS Code severity when displaying in the problems window. You can override specific `jac` error codes `{ "error": "Error", "note": "Information", "name-defined": "Warning" }`                                                             |
| jaseci.interpreter       | `[]`                                          | Path to a Python interpreter to use to run the Jaseci language server. When set to `[]`, the interpreter for the workspace is obtained from `ms-python.python` extension. If set to some path, that path takes precedence, and the Python extension is not queried for the interpreter. |
| jaseci.importStrategy    | `useBundled`                                  | Setting to choose where to load `jaclang` from. `useBundled` picks jaclang bundled with the extension. `fromEnvironment` uses `jaclang` available in the environment.                                                                                                                   |
| jaseci.showNotifications | `off`                                         | Setting to control when a notification is shown.                                                                                                                                                                                                                                        |
| jaseci.reportingScope    | `file`                                        | (experimental) Setting to control if problems are reported for files open in the editor (`file`) or for the entire workspace (`workspace`).                                                                                                                                             |

## Commands

| Command                | Description                         |
| ---------------------- | ----------------------------------- |
| Jaseci: Restart Server | Force re-start the language server. |

## Logging

From the command palette (View > Command Palette ...), run the `Developer: Set Log Level...` command. From the quick pick menu, select `Jaseci Language Server` extension from the `Extension logs` group. Then select the log level you want to set.

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

Then you can install the extension on your VSCode using this https://code.visualstudio.com/docs/editor/extension-marketplace
