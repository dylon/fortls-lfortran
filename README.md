# FortLS-LFortran VSCode Extension

This extension demonstrates how to utilize `lfortran` as the backend of a
Fortran language server for VSCode that uses `pygls` to implement Microsoft's
language server protocol (LSP). Currently, it supports linting and identifying
Fortran errors in your sources, but it can easily be extended with additional
functionality.

## Dependencies

To build the extension, you will need the following:
1. NodeJS with NPM
2. Python >= 3.11 with Pip

## Building and Installation

Clone the repository from github:

```shell
git clone https://github.com/dylon/fortls-lfortran.git
cd fortls-lfortran
```

Install the dependencies:

```shell
npm install
```

Build the extension:

```shell
npx vsce package
```

The JavaScript/ECMAScript/TypeScript dependencies will be bundled with the
extension's client, and the Python dependencies will be installed alongside the
extension's language server.

The extension may then be installed from the compiled `.vsix` file:
1. Click the `"Extensions"` tab or press `Ctrl + Shift + x`.
2. Near the top-right of the panel that opens, click the horizontal ellipsis
   that has the tooltip text `"Views and More Actions..."`.
3. Click `"Install from VSIX..."`
4. Open the `fortls-lfortran-0.0.1.vsix` package you just created.

### Updating the extension

If you need to update the extension, please rebuild it as above and then perform
the following actions:
1. Click the `"Extensions"` tab or press `Ctrl + Shift + x`.
2. Find the listing for `lfortran-lsp`.
3. Click the gear icon with the tooltip text `"Manage"`
4. Click `"Uninstall"`.
5. Click `"Restart Extensions"` on the `lfortran-lsp` listing where the gear
   icon used to be.
6. Wait a moment for the extensions to reload.
7. Click the `"Refresh"` button near the top-right of the extensions panel (it
   looks like an arrow that is rotating to the right).
8. Wait a moment for the extensions to reload.
9. Reinstall the .vsix archive as before:
   1. Near the top-right of the extensions panel, click the horizontal ellipsis
      that has the tooltip text `"Views and More Actions..."`.
   2. Click `"Install from VSIX..."`
   3. Open the `fortls-lfortran-0.0.1.vsix` package you just created.

## Configuration

Once the plugin has been installed, you may configure it as follows:
1. Click the `"File"` menu.
2. Expand the `"Preferences"` sub-menu.
3. Click `"Settings"`.
4. Expand the `"Extensions"` tree.
5. Click `"FortLS LFortran Language Server"`.
6. Configure it as desired.

If you wish to pass flags to `lfortran`, such as the include directories where
you have compiled the `.mod` files for your Fortran project, you may add them as
individual strings to the `FortLSLFortranLanguageServer.compiler.flags` array.
Configuration the `flags` array will open the JSON settings editor. Just add
each option, individually, as an array element of type string, e.g.:

```json
{
    "FortLSLFortranLanguageServer.compiler.flags": [
        "-I/path/to/lfortran/mod/files"
    ]
}
```

By default, the extension will attempt to pull the path to `lfortran` from your
`$PATH` environment variable. If it cannot find it on your path or you would
prefer to use `lfortran` from another location, please specify the location in
the `FortLSLFortranLanguageServer.compiler.lfortranPath` field.

Likewise, the extension will attempt to locate an acceptable version of Python.
If you need to override its selection, please specify the path to your desired
`python` executable by editing `FortLSLFortranLanguageServer.server.pythonPath`.

## How it works

The
[activate](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L69)
function of the client serves as the entry point to the extension. It is called by VSCode when the extension is initialized.

`activate` attempts to locate a valid
[python](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L76-L81)
executable. If one cannot be found, it will terminate without attempting to
start the language server.

If a valid `python` executable is found, it is used to [start the language
server](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L91).

The extension will then [locate the path to the Python language
server](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L118).
This is executed with `python` as a script.

The options to execute the server are defined,
[here](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L132-L138).
They include the path to the `python` executable as the value of `command`, as
well as any additional (e.g. debug) `python` parameters and the path to the
language server script as the value of `args`. The current environment is passed
as the value of `options > env` so things such as `lfortran` may be located from
your `$PATH`.

The options for how VSCode interacts with the extension are defined,
[here](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L140-L151).
They include the `documentSelector`, which selects the documents associated with
this extension (i.e. fortran files), where to log messages as part of
`outputChannel`, and things such as the maximum number of times to restart the
extension if it fails.

Finally, a new VSCode client is initialized with the options and started,
[here](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/client/src/extension.ts#L153-L158).

When the client is started, the server is executed using the server options,
above. The main entry point is located,
[here](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L148-L162).
It contains several methods of communication, but the one needed for the
extension to work in VSCode is the default [I/O
mechanism](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L158).

The language server is implemented using the `pygls` LSP framework. With it, you
first [instantiate an instance of
pygls.server.LanguageServer](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L65-L69),
and use that instance to decorate your event handlers for specific LSP
operations. We have implemented a
[subclass](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L56-L62)
of `LanguageServer` as that was how `pygls` did it in its example, but you may
use `LanguageServer` directly. You may also customize any LSP initialization
logic by overriding the logic of
[LFortranLanguageServerProtocol.lsp_initialize](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L49-L53).

To implement an LSP event handler, you decorate the respective handler with the
`feature` method of your `LanguageServer` instance, as we have done for the
[handler](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L111-L118)
that is called when a document is edited, `text_document_did_change`. Our event
handlers are also decorated with
[catch_and_log_exception](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L33-L42),
which logs any unhandled errors to the VSCode extension's output terminal.


`@server.feature` requires the first parameter to be a supported LSP string
identifier (enumerated by the `lsprotocol.types` package). It accepts an
optional, second parameter for options that affect the event handler. Event
handlers must return an instance of the expected type or behave as expected by
the [LSP
specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
associated with the handler. The first parameter to the event handlers is `ls`
by convention, which `pygls` understands to be the `LanguageServer` instance.

Presently, we have event handlers that lint and report errors in opened files.
The event handlers call
[validate_text_document](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L77-L87).
This function first [retrieves the
configuration](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L80-L85)
for the affected document, then calls
[lfortran.show_errors](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L86)
to get the list of diagnostics. Finally, it [reports the
diagnostics](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_language_server.py#L87)
to VSCode.

`show_errors` [calls
lfortran](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L267-L274)
with the necessary command-line options to lint the source code, then [parses
then as
JSON](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L282)
and [translates them to
diagnostics](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L287-L307)
before [returning the
list](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L309).

`run_compiler`, used for calling `lfortran`, first [creates a temporary
file](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L90)
to pass the current file's text to `lfortran`. This is necessary because the
file may have been edited and not saved, in which case the text to lint is not
the text in the file's path. It then [resets the file location to
0](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L95)
so `lfortran` will read it from the beginning (the file will appear empty to `lfortran`, otherwise).

The correct path to `lfortran` is
[identified](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L97-L107),
the command for invoking `lfortran` is
[constructed](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L109-L110),
and it is
[called](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L112-L116).
`stdout` and `stderr` are combined into `stdout` for brevity, which is
retrieved,
[here](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L117).
The output is then
[returned](https://github.com/dylon/fortls-lfortran/blob/90e35ad5617d3c4baf3ed193a9416a5c4369954e/server/src/lflsp/lfortran_accessor.py#L121),
verbatim, so the caller may parse it however it desires.
