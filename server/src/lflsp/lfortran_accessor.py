import atexit
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Self

from lsprotocol import converters, types as lsp

from cattrs import Converter


logger = logging.getLogger(__name__)

RE_FILE_URI: re.Pattern = re.compile(r"^file:(?:\/\/)?")


class LFortranAccessor(ABC):

    @abstractmethod
    def resolve(self: Self,
                uri: str,
                filename: str,
                flags: List[str],
                resolved: Optional[Dict[str, str]]) -> str:
        raise NotImplementedError("resolve not yet implemented")

    @abstractmethod
    def version(self: Self, settings: Dict[str, Any]) -> str:
        raise NotImplementedError("version not yet implemented")

    @abstractmethod
    def show_document_symbols(self: Self,
                              uri: str,
                              text: str,
                              settings: Dict[str, Any]) -> List[lsp.SymbolInformation]:
        raise NotImplementedError("show_document_symbols not yet implemented")

    @abstractmethod
    def lookup_name(self: Self,
                    uri: str,
                    text: str,
                    line: int,
                    column: int,
                    settings: Dict[str, Any]) -> List[lsp.DefinitionLink]:
        raise NotImplementedError("lookup_name not yet implemented")

    @abstractmethod
    def show_errors(self: Self,
                    uri: str,
                    text: str,
                    settings: Dict[str, Any]) -> List[lsp.Diagnostic]:
        raise NotImplementedError("show_errors not yet implemented")

    @abstractmethod
    def rename_symbol(self: Self,
                      uri: str,
                      text: str,
                      line: int,
                      column: int,
                      new_name: str,
                      settings: Dict[str, Any]) -> List[lsp.TextEdit]:
        raise NotImplementedError("rename_symbol not yet implemented")


class LFortranCLIAccessor(LFortranAccessor):
    converter: Converter
    show_message_log: Callable

    def __init__(self: Self, show_message_log: Callable) -> None:
        self.converter = converters.get_converter()
        self.show_message_log = show_message_log

    @staticmethod
    def check_path_exists_and_is_executable(path: str) -> bool:
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def run_compiler(self: Self,
                     settings: Dict[str, Any],
                     params: List[str],
                     text: str,
                     default_value: str = "",
                     no_response_is_success: bool = False) -> str:
        output: str = default_value

        with tempfile.NamedTemporaryFile(prefix="fortls-lfortran-lsp-", suffix=".tmp", mode="w+t") as f:
            f.write(text)

            # NOTE: Reset the file location so lfortran can read it before the
            # tempfile is closed and deleted.
            f.seek(0)

            lfortran_path: Optional[str] = settings["compiler"]["lfortranPath"]

            if lfortran_path is not None and \
               (lfortran_path == "lfortran" or \
                not self.check_path_exists_and_is_executable(lfortran_path)):
                lfortran_path = shutil.which("lfortran")

            if lfortran_path is None or \
               not self.check_path_exists_and_is_executable(lfortran_path):
                self.show_message_log(f"lfortran_path = [{lfortran_path}] is not executable.")
                return output

            params = params + settings["compiler"]["flags"] + [f.name]
            command: List[str] = [lfortran_path] + params

            result = subprocess.run(command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            output = result.stdout  # includes stdout and stderr

            self.show_message_log(f"command = `{' '.join(command)}`, output = {output}")

        return output

    def resolve(self: Self,
                uri: str,
                filename: str,
                flags: List[str],
                resolved: Optional[Dict[str, str]]) -> str:
        file_path: str = filename

        if file_path.endswith(".tmp"):
            file_path = uri

        file_path = re.sub(RE_FILE_URI, "", file_path)

        if os.path.isfile(file_path):
            file_path = os.path.realpath(file_path)
        else:
            resolution: Optional[str] = None
            if resolved is not None:
                resolution = resolved.get(file_path, None)
            if resolution is None:
                for flag in flags:
                    if flag.startswith("-I"):
                        include_dir: str = flag[2:]
                        resolution = os.path.join(include_dir, file_path)
                        if os.path.isfile(resolution):
                            resolution = os.path.realpath(resolution)
                            if resolved is not None:
                                resolved[file_path] = resolution
                            file_path = resolution
                            break
            else:
                file_path = resolution

        return file_path

    def version(self: Self, settings: Dict[str, Any]) -> str:
        params: List[str] = ["--version"]
        output: str = self.run_compiler(settings, params, "")
        return output

    def show_document_symbols(self: Self,
                              uri: str,
                              text: str,
                              settings: Dict[str, Any]) -> List[lsp.SymbolInformation]:
        params: List[str] = ["--show-document-symbols", "--continue-compilation"]
        output: str = self.run_compiler(settings, params, text, default_value="[]")

        json_symbols: List[Dict[str, Any]]

        try:
            json_symbols = json.loads(output)
        except Exception as e:
            self.show_message_log(f"show_document_symbols failed: {e}")
            json_symbols = []

        lsp_symbols: List[lsp.SymbolInformation] = []

        resolved: Dict[str, str] = {}
        for json_symbol in json_symbols:
            symbol_path: str = self.resolve(
                uri,
                json_symbol["filename"],
                settings["compiler"]["flags"],
                resolved
            )

            lsp_symbol: lsp.SymbolInformation = \
                self.converter.structure(json_symbol, lsp.SymbolInformation)

            lsp_location: lsp.Location = symbol.location
            lsp_location.uri = symbol_path

            lsp_range: lsp.Range = lsp_location.range

            lsp_start: lsp.Position = lsp_range.start
            lsp_start.line -= 1
            lsp_start.character -= 1

            lsp_end: lsp.Position = lsp_range.end
            lsp_end.line -= 1
            lsp_end.character -= 1

            lsp_symbols.append(lsp_symbol)

        return lsp_symbols

    def lookup_name(self: Self,
                    uri: str,
                    text: str,
                    line: int,
                    column: int,
                    settings: Dict[str, Any]) -> List[lsp.DefinitionLink]:

        params: List[str] = [
            "--lookup-name",
            f"--line=${line + 1}",
            f"--column=${column + 1}",
            "--continue-compilation"
        ]

        output: str = self.run_compiler(settings, params, text, default_value="[]")
        json_records: List[Dict[str, Any]]

        try:
            json_records = json.loads(output)
        except Exception as e:
            self.show_message_log(f"lookup_name failed: {e}")
            json_records = []

        lsp_definitions: List[lsp.DefinitionLink] = []

        for json_record in json_records:
            symbol_path: str = self.resolve(
                uri,
                json_record["filename"],
                settings["compiler"]["flags"]
            )

            lsp_location: lsp.Location = \
                self.converter.structure(lsp_record["location"], lsp.Location)

            lsp_range: lsp.Range = lsp_location.range

            lsp_start: lsp.Position = lsp_range.start
            lsp_start.line -= 1
            lsp_start.character -= 1

            lsp_end: lsp.Position = lsp_range.end
            lsp_end.line -= 1
            lsp_end.character -= 1

            lsp_definition: lsp.DefinitionLink = lsp.DefinitionLink()
            lsp_definition.target_uri = symbol_path
            lsp_definition.target_range = lsp_location.range
            lsp_definition.target_selection_range = lsp_location.range

            lsp_definitions.append(lsp_definition)

        return lsp_definitions

    def show_errors(self: Self,
                    uri: str,
                    text: str,
                    settings: Dict[str, Any]) -> List[lsp.Diagnostic]:

        params: List[str] = [
            "--show-errors",
            "--continue-compilation"
        ]

        output: str = self.run_compiler(settings, params, text,
                                        default_value="{}",
                                        no_response_is_success=True)

        lsp_diagnostics: List[lsp.Diagnostic] = []

        if len(output) > 0:
            json_records: Dict[str, Any]

            try:
                json_records = json.loads(output)
            except Exception as e:
                self.show_message_log(f"show_errors failed: {e}")
                json_records = {}

            if "diagnostics" in json_records:
                json_diagnostics = json_records["diagnostics"]
                k: int = min(len(json_diagnostics), settings["maxNumberOfProblems"])
                for i in range(k):
                    json_diagnostic: Dict[str, any] = json_diagnostics[i]

                    lsp_diagnostic = \
                        self.converter.structure(json_diagnostic, lsp.Diagnostic)

                    lsp_diagnostic.source = "lfortran"

                    lsp_range: lsp.Range = lsp_diagnostic.range

                    lsp_start: lsp.Position = lsp_range.start
                    lsp_start.line -= 1
                    lsp_start.character -= 1

                    lsp_end: lsp.Position = lsp_range.end
                    lsp_end.line -= 1

                    lsp_diagnostics.append(lsp_diagnostic)

        return lsp_diagnostics

    def rename_symbol(self: Self,
                      uri: str,
                      text: str,
                      line: int,
                      column: int,
                      new_name: str,
                      settings: Dict[str, Any]) -> List[lsp.TextEdit]:

        params: List[str] = [
            "--rename-symbol",
            f"--line=${line + 1}",
            f"--column=${column + 1}",
            "--continue-compilation"
        ]

        output: str = \
            self.run_compiler(settings, params, text, default_value="[]")

        json_records: List[Dict[str, Any]]

        try:
            json_records = json.loads(output)
        except Exception as e:
            self.show_message_log(f"rename_symbol failed: {e}")
            json_records = []

        lsp_edits: List[lsp.TextEdit] = []

        for json_record in json_records:
            if "location" in json_record:
                json_location: Dict[str, Any] = json_record["location"]
                json_range = json_location["range"]
                lsp_range: lsp.Range = \
                    self.converter.structure(json_range, lsp.Range)

                lsp_start: lsp.Position = lsp_range.start
                lsp_start.line -= 1
                lsp_start.column -= 1

                lsp_end: lsp.Position = lsp_range.end
                lsp_end.line -= 1
                lsp_end.column -= 1

                lsp_edit: lsp.TextEdit = lsp.TextEdit()
                lsp_edit.range = lsp_range
                lsp_edit.new_text = new_name

                lsp_edits.append(lsp_edit)

        return lsp_edits
