"use strict";

import * as net from "net";
import * as path from "path";
import { ExtensionContext, ExtensionMode, workspace, extensions, window, commands } from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";
import { exec } from "child_process";

let client: LanguageClient;

function getClientOptions(): LanguageClientOptions {
	return {
		// Register the server for plain text documents
		documentSelector: [
			{ scheme: "file", language: "jac" },
			{ scheme: "untitled", language: "jac" },
		],
		outputChannelName: "Jaseci Language Server",
		synchronize: {
			// Notify the server about file changes to '.clientrc files contain in the workspace
			fileEvents: workspace.createFileSystemWatcher("**/.clientrc"),
		},
	};
}

function startLangServerTCP(addr: number): LanguageClient {
	const serverOptions: ServerOptions = () => {
		return new Promise((resolve /*, reject */) => {
			const clientSocket = new net.Socket();
			clientSocket.connect(addr, "127.0.0.1", () => {
				resolve({
					reader: clientSocket,
					writer: clientSocket,
				});
			});
		});
	};

	return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, getClientOptions());
}

function startLangServer(command: string, args: string[], cwd: string): LanguageClient {
	const serverOptions: ServerOptions = {
		args,
		command,
		options: { cwd },
	};

	return new LanguageClient(command, serverOptions, getClientOptions());
}

// export function activate(context: ExtensionContext): void {
// 	if (context.extensionMode === ExtensionMode.Development) {
// 		// Development - Run the server manually
// 		client = startLangServerTCP(2087);
// 	} else {
// 		// Production - Client is going to run the server (for use within `.vsix` package)
// 		const cwd = path.join(__dirname, "..", "..");
// 		const pythonPath = workspace.getConfiguration("jac").get<string>("pythonPath");

// 		if (!pythonPath) {
// 			throw new Error("`jac.pythonPath` is not set");
// 		}

// 		client = startLangServer(pythonPath, ["-m", "server"], cwd);
// 	}

// 	context.subscriptions.push(client.start());
// }

export async function activate(context: ExtensionContext): Promise<void> {
	// Getting the Python Path
	let pythonPath = workspace.getConfiguration("jac").get<string>("pythonPath");
	if (!pythonPath) {
		const py_ext = extensions.getExtension("ms-python.python");
		if (!py_ext) {
			await py_ext.activate();
		}
		pythonPath = await py_ext.exports.settings.getExecutionDetails().execCommand[0];
		if (!pythonPath) {
			const result = await window.showErrorMessage(
				"Unable to start the jac language server. \n Select a Python interpreter first where Jaseci is installed.",
				"Select Python Interpreter"
			);
			if (result === "Select Python Interpreter") {
				await commands.executeCommand("python.setInterpreter");
			}
			pythonPath = await py_ext.exports.settings.getExecutionDetails().execCommand[0];
			await workspace.getConfiguration("jac").update("pythonPath", pythonPath);
		}
	}
	// Installing requirements
	const reqs = path.join(path.join(__dirname, "..", ".."), "requirements.txt");
	exec(`${pythonPath} pip install -r ${reqs}`);

	if (context.extensionMode === ExtensionMode.Development) {
		// Development - Run the server manually
		client = startLangServerTCP(2087);
	} else {
		// Production - Client is going to run the server (for use within `.vsix` package)
		const cwd = path.join(__dirname, "..", "..");

		if (!pythonPath) {
			throw new Error("`jac.pythonPath` is not set");
		}

		client = startLangServer(pythonPath, ["-m", "server"], cwd);
	}

	context.subscriptions.push(client.start());
}


export function deactivate(): Thenable<void> {
	return client ? client.stop() : Promise.resolve();
}
