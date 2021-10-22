# Copyright (c) Facebook, Inc. and its affiliates.
import gzip
import lzma
import os
import tarfile
import zipfile

from enum import Enum
from io import IOBase
from torchdata.datapipes import functional_datapipe
from torchdata.datapipes.iter import IterDataPipe
from torchdata.datapipes.utils import StreamWrapper
from typing import Iterator, Optional, Tuple, Union


class CompressionType(Enum):
    GZIP = "gzip"
    LZMA = "lzma"
    TAR = "tar"
    ZIP = "zip"


@functional_datapipe("extract")
class ExtractorIterDataPipe(IterDataPipe[Tuple[str, IOBase]]):
    r"""
    Iterable DataPipe

    Args:
        source_datapipe: DataPipe
        file_type:
    """

    types = CompressionType

    _DECOMPRESSORS = {
        types.GZIP: lambda file: gzip.GzipFile(fileobj=file),
        types.LZMA: lambda file: lzma.LZMAFile(file),
        types.TAR: lambda file: tarfile.open(fileobj=file, mode="r:*"),
        types.ZIP: lambda file: zipfile.ZipFile(file=file),
    }

    def __init__(
        self, source_datapipe: IterDataPipe[Tuple[str, IOBase]], file_type: Optional[Union[str, CompressionType]] = None
    ) -> None:
        self.source_datapipe: IterDataPipe[Tuple[str, IOBase]] = source_datapipe
        if isinstance(file_type, str):
            file_type = self.types(file_type.lower())
        self.file_type: Optional[CompressionType] = file_type

    def _detect_compression_type(self, path: str) -> CompressionType:
        if self.file_type:
            return self.file_type

        ext = os.path.splitext(path)[1]
        if ext == ".gz":
            return self.types.GZIP
        elif ext == ".xz":
            return self.types.LZMA
        elif ext == ".tar":
            return self.types.TAR
        elif ext == ".zip":
            return self.types.ZIP
        else:
            raise RuntimeError(
                f"File at {path} has file extension {ext}, which does not match what are supported by"
                f"ExtractorIterDataPipe."
            )

    def __iter__(self) -> Iterator[Tuple[str, IOBase]]:
        for path, file in self.source_datapipe:
            file_type = self._detect_compression_type(path)
            decompressor = self._DECOMPRESSORS[file_type]
            yield path, StreamWrapper(decompressor(file))

    def __len__(self):
        return len(self.source_datapipe)
