/* -------------------------------------------------------------------------
 * Original work Copyright (c) Microsoft Corporation. All rights reserved.
 * Original work licensed under the MIT License.
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Open Law Library. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ----------------------------------------------------------------------- */
"use strict";

import path from "path";

import { spawnSync } from "node:child_process";

import * as net from "net";
import * as path from "path";
import * as vscode from "vscode";
import * as semver from "semver";

import which from "which";

import { PythonExtension } from "@vscode/python-extension";
import { LanguageClient, LanguageClientOptions, ServerOptions, State, integer } from "vscode-languageclient/node";

const MIN_PYTHON = semver.parse("3.11.0")

// Some other nice to haves.
// TODO: Check selected env satisfies pygls' requirements - if not offer to run the select env command.
// TODO: TCP Transport
// TODO: WS Transport
// TODO: Web Extension support (requires WASM-WASI!)

let client: LanguageClient;
let clientStarting = false
let python: PythonExtension;
let logger: vscode.LogOutputChannel

const RE_PYTHON_VERSION = /^Python (?<major>[0-9]+)\.(?<minor>[0-9]+)\.(?<micro>[0-9]+)$/;

function satisfiesMinPythonVersion(pythonVersion: string): boolean {
  const versionMatch = RE_PYTHON_VERSION.exec(pythonVersion);
  const majorVersion = parseInt(versionMatch.groups.major, 10);
  const minorVersion = parseInt(versionMatch.groups.minor, 10);
  // const microVersion = parseInt(versionMatch.groups.micro, 10);
  return (majorVersion === 3) && (minorVersion >= 11);
}

/**
 * This is the main entry point.
 * Called when vscode first activates the extension
 */
export async function activate(context: vscode.ExtensionContext) {
  logger = vscode.window.createOutputChannel('FortLS LFortran Language Server', { log: true });
  logger.info("Extension activated.");

  await getPythonExtension();
  if (!python) {
    logger.info("[1] No python, returning ...");
    return;
  }

  // Restart language server command
  context.subscriptions.push(
    vscode.commands.registerCommand("FortLSLFortranLanguageServer.server.restart", async () => {
      logger.info('restarting server...');
      await startLangServer();
    })
  )

  // Execute command... command
  context.subscriptions.push(
    vscode.commands.registerCommand("FortLSLFortranLanguageServer.server.executeCommand", async () => {
      logger.info("Executing command ...");
      await executeServerCommand();
    })
  )

  // Restart the language server if the user switches Python envs...
  context.subscriptions.push(
    python.environments.onDidChangeActiveEnvironmentPath(async () => {
      logger.info('python env modified, restarting server...')
      await startLangServer();
    })
  )

  // ... or if they change a relevant config option
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(async (event) => {
      if (event.affectsConfiguration("FortLSLFortranLanguageServer.server") || event.affectsConfiguration("FortLSLFortranLanguageServer.client")) {
        logger.info('config modified, restarting server...');
        await startLangServer();
      }
    })
  )

  // Start the language server once the user opens the first text document...
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(
      async () => {
        if (!client) {
          logger.info("[1] No client, starting lang server ...");
          await startLangServer();
        }
      }
    )
  )

  // ...or notebook.
  context.subscriptions.push(
    vscode.workspace.onDidOpenNotebookDocument(
      async () => {
        if (!client) {
          logger.info("[2] No client, starting lang server ...");
          await startLangServer();
        }
      }
    )
  )

  // Restart the server if the user modifies it.
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document: vscode.TextDocument) => {
      const expectedUri = vscode.Uri.file(getServerPath());

      if (expectedUri.toString() === document.uri.toString()) {
        logger.info('server modified, restarting...');
        await startLangServer();
      }
    })
  )
}

export function deactivate(): Thenable<void> {
  return stopLangServer();
}

/**
 * Start (or restart) the language server.
 *
 * @param command The executable to run
 * @param args Arguments to pass to the executable
 * @returns
 */
async function startLangServer() {

  // Don't interfere if we are already in the process of launching the server.
  if (clientStarting) {
    logger.info("clientStarging, returning ...");
    return
  }

  clientStarting = true
  if (client) {
    await stopLangServer()
  }
  const config = vscode.workspace.getConfiguration("FortLSLFortranLanguageServer.server")
  const serverPath = getServerPath()

  logger.info(`server: '${serverPath}'`)

  const resource = vscode.Uri.file(serverPath)
  const pythonCommand = await getPythonCommand(resource)
  if (!pythonCommand) {
    logger.info("no pythonCommand, returning ...");
    clientStarting = false
    return
  }

  // logger.debug(`python: ${pythonCommand.join(" ")}`)
  logger.info(`python: ${pythonCommand.join(" ")}`)
  const serverOptions: ServerOptions = {
    command: pythonCommand[0],
    args: [...pythonCommand.slice(1), serverPath]
  };

  // client = new LanguageClient(
  //   "FortLSLFortranLanguageServer",
  //   "FortLS LFortran Language Server",
  //   serverOptions,
  //   getClientOptions());
  client = new LanguageClient(
    "fortran",
    "FortLS-LFortran Language Server",
    serverOptions,
    getClientOptions());
  const promises = [client.start()]

  if (config.get<boolean>("debug")) {
    promises.push(startDebugging())
  }

  const results = await Promise.allSettled(promises)
  clientStarting = false

  for (const result of results) {
    if (result.status === "rejected") {
      logger.error(`There was a error starting the server: ${result.reason}`)
    }
  }
}

async function stopLangServer(): Promise<void> {
  logger.info("Stopping lang server ...");
  if (!client) {
    logger.info("No client to stop, returning...");
    return
  }

  if (client.state === State.Running) {
    await client.stop();
    logger.info("Client stopped ...");
  }

  client.dispose()
  client = undefined
}

function startDebugging(): Promise<void> {
  if (!vscode.workspace.workspaceFolders) {
    logger.error("Unable to start debugging, there is no workspace.");
    return Promise.reject("Unable to start debugging, there is no workspace.");
  }
  // TODO: Is there a more reliable way to ensure the debug adapter is ready?
  setTimeout(async () => {
    await vscode.debug.startDebugging(vscode.workspace.workspaceFolders[0], "fortls-lfortran: Debug Server");
  }, 2000);
}

function getClientOptions(): LanguageClientOptions {
  const config = vscode.workspace.getConfiguration('FortLSLFortranLanguageServer.client')
  const options = {
    documentSelector: config.get<any>('documentSelector'),
    outputChannel: logger,
    connectionOptions: {
      maxRestartCount: 0 // don't restart on server failure.
    },
  };
  logger.info(`client options: ${JSON.stringify(options, undefined, 2)}`)
  return options
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

  return new LanguageClient(
    `tcp lang server (port ${addr})`,
    serverOptions,
    getClientOptions()
  );
}

/**
 * Execute a command provided by the language server.
 */
async function executeServerCommand() {
  if (!client || client.state !== State.Running) {
    await vscode.window.showErrorMessage("There is no language server running.")
    return
  }

  const knownCommands = client.initializeResult.capabilities.executeCommandProvider?.commands
  if (!knownCommands || knownCommands.length === 0) {
    const info = client.initializeResult.serverInfo
    const name = info?.name || "Server"
    const version = info?.version || ""

    await vscode.window.showInformationMessage(`${name} ${version} does not implement any commands.`)
    return
  }

  const commandName = await vscode.window.showQuickPick(knownCommands, { canPickMany: false })
  if (!commandName) {
    return
  }
  logger.info(`executing command: '${commandName}'`)

  const result = await vscode.commands.executeCommand(commandName /* if your command accepts arguments you can pass them here */)
  logger.info(`${commandName} result: ${JSON.stringify(result, undefined, 2)}`)
}

/**
 *
 * @returns The python script that implements the server.
 */
function getServerPath(): string {
  const server = path.join(__dirname, "server", "python", "lflsp", "lfortran_language_server.py")
  return server
}

/**
 * Return the python command to use when starting the server.
 *
 * If debugging is enabled, this will also included the arguments to required
 * to wrap the server in a debug adapter.
 *
 * @returns The full python command needed in order to start the server.
 */
async function getPythonCommand(resource?: vscode.Uri): Promise<string[] | undefined> {
  const config = vscode.workspace.getConfiguration("FortLSLFortranLanguageServer.server", resource)
  const pythonPath = await getPythonInterpreter(resource)
  if (!pythonPath) {
    logger.info("No pythonPath, returning ...");
    return;
  }
  const command = [pythonPath];
  const enableDebugger = config.get<boolean>('debug');

  if (!enableDebugger) {
    return command;
  }

  const debugHost = config.get<string>('debugHost');
  const debugPort = config.get<integer>('debugPort');
  try {
    const debugArgs = await python.debug.getRemoteLauncherCommand(debugHost, debugPort, true);
    // Debugpy recommends we disable frozen modules
    command.push("-Xfrozen_modules=off", ...debugArgs);
  } catch (err) {
    logger.error(`Unable to get debugger command: ${err}`);
    logger.error("Debugger will not be available.");
  }

  return command;
}

/**
 * Return the python interpreter to use when starting the server.
 *
 * This uses the official python extension to grab the user's currently
 * configured environment.
 *
 * @returns The python interpreter to use to launch the server
 */
async function getPythonInterpreter(resource?: vscode.Uri): Promise<string | undefined> {
  const config = vscode.workspace.getConfiguration("FortLSLFortranLanguageServer.server", resource);
  let pythonPath = config.get<string>('pythonPath');
  if (pythonPath) {
    logger.info(`Using user configured python environment: '${pythonPath}'`);
    return pythonPath;
  }

  if (!python) {
    pythonPath = await which("python3", { nothrow: true });
    if (pythonPath) {
      const options = {
        encoding: "utf-8",
        stdio: "pipe",
      };
      let pythonVersion = await spawnSync(pythonPath, ["--version"], options);
      if (!satisfiesMinPythonVersion(pythonVersion)) {
        pythonPath = await which("python", { nothrow: true });
        if (pythonPath) {
          pythonVersion = await spawnSync(pythonPath, ["--version"], options);
        }
      }
      if (satisfiesMinPythonVersion(pythonVersion)) {
        logger.info(`Using python from \$PATH: '${pythonPath}'`);
        return pythonPath;
      }
    }
    logger.info("[2] No python, returning ...");
    return;
  }

  if (resource) {
    logger.info(`Looking for environment in which to execute: '${resource.toString()}'`);
  }

  // Use whichever python interpreter the user has configured.
  const activeEnvPath = python.environments.getActiveEnvironmentPath(resource);
  logger.info(`Found environment: ${activeEnvPath.id}: ${activeEnvPath.path}`);

  const activeEnv = await python.environments.resolveEnvironment(activeEnvPath);
  if (!activeEnv) {
    logger.error(`Unable to resolve envrionment: ${activeEnvPath}`);
    return;
  }

  const v = activeEnv.version;
  const pythonVersion = semver.parse(`${v.major}.${v.minor}.${v.micro}`);

  // Check to see if the environment satisfies the min Python version.
  if (semver.lt(pythonVersion, MIN_PYTHON)) {
    const message = [
      `Your currently configured environment provides Python v${pythonVersion} `,
      `but FortLSLFortranLanguageServer requires v${MIN_PYTHON}.\n\nPlease choose another environment.`
    ].join('');

    const response = await vscode.window.showErrorMessage(message, "Change Environment");
    if (!response) {
      logger.info("No response! Returning ...");
      return;
    } else {
      await vscode.commands.executeCommand('python.setInterpreter');
      logger.info("Set the Python interpreter ...");
      return;
    }
  }

  const pythonUri = activeEnv.executable.uri;
  if (!pythonUri) {
    logger.error(`URI of Python executable is undefined!`);
    return;
  }

  return pythonUri.fsPath;
}

async function getPythonExtension() {
  try {
    python = await PythonExtension.api();
  } catch (err) {
    logger.error(`Unable to load python extension: ${err}`);
  }
}
