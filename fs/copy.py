"""Functions for copying resources *between* filesystem.
"""

from __future__ import print_function, unicode_literals

import typing
import warnings

from .errors import ResourceNotFound
from .opener import manage_fs
from .path import abspath, combine, frombase, normpath
from .tools import is_thread_safe
from .walk import Walker

if typing.TYPE_CHECKING:
    from typing import Callable, Optional, Text, Union
    from .base import FS

    _OnCopy = Callable[[FS, Text, FS, Text], object]


def copy_fs(
    src_fs,  # type: Union[FS, Text]
    dst_fs,  # type: Union[FS, Text]
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Copy the contents of one filesystem to another.

    Arguments:
        src_fs (FS or str): Source filesystem (URL or instance).
        dst_fs (FS or str): Destination filesystem (URL or instance).
        walker (~fs.walk.Walker, optional): A walker object that will be
            used to scan for files in ``src_fs``. Set this if you only want
            to consider a sub-set of the resources in ``src_fs``.
        on_copy (callable): A function callback called after a single file copy
            is executed. Expected signature is ``(src_fs, src_path, dst_fs,
            dst_path)``.
        workers (int): Use `worker` threads to copy data, or ``0`` (default) for
            a single-threaded copy.

    """
    return copy_fs_if(src_fs, dst_fs, "always", walker, on_copy, workers)


def copy_fs_if_newer(
    src_fs,  # type: Union[FS, Text]
    dst_fs,  # type: Union[FS, Text]
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Use ``copy_fs_if`` instead."""
    warnings.warn(
        DeprecationWarning("copy_fs_if_newer is deprecated. Use copy_fs_if instead.")
    )
    return copy_fs_if(src_fs, dst_fs, "newer", walker, on_copy, workers)


def copy_fs_if(
    src_fs,  # type: Union[FS, Text]
    dst_fs,  # type: Union[FS, Text]
    condition="always",  # type: Text
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Copy the contents of one filesystem to another, depending on a condition.

    Depending on the value of ``strategy``, certain conditions must be fulfilled
    for a file to be copied to ``dst_fs``. The following values
    are supported:

    ``"always"``
        The source file is always copied.
    ``"newer"``
        The last modification time of the source file must be newer than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"older"``
        The last modification time of the source file must be older than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"exists"``
        The source file is only copied if a file of the same path already exists in ``dst_fs``.
    ``"not_exists"``
        The source file is only copied if no file of the same path already exists in ``dst_fs``.


    Arguments:
        src_fs (FS or str): Source filesystem (URL or instance).
        dst_fs (FS or str): Destination filesystem (URL or instance).
        condition (str): Name of the condition to check for each file.
        walker (~fs.walk.Walker, optional): A walker object that will be
            used to scan for files in ``src_fs``. Set this if you only want
            to consider a sub-set of the resources in ``src_fs``.
        on_copy (callable):A function callback called after a single file copy
            is executed. Expected signature is ``(src_fs, src_path, dst_fs,
            dst_path)``.
        workers (int): Use ``worker`` threads to copy data, or ``0`` (default) for
            a single-threaded copy.

    """
    return copy_dir_if(
        src_fs,
        "/",
        dst_fs,
        "/",
        condition,
        walker=walker,
        on_copy=on_copy,
        workers=workers,
    )


def copy_file(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
):
    # type: (...) -> None
    """Copy a file from one filesystem to another.

    If the destination exists, and is a file, it will be first truncated.

    Arguments:
        src_fs (FS or str): Source filesystem (instance or URL).
        src_path (str): Path to a file on the source filesystem.
        dst_fs (FS or str): Destination filesystem (instance or URL).
        dst_path (str): Path to a file on the destination filesystem.

    """
    copy_file_if(src_fs, src_path, dst_fs, dst_path, "always")


def copy_file_if_newer(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
):
    # type: (...) -> bool
    """Use ``copy_file_if`` instead."""
    warnings.warn(
        DeprecationWarning(
            "copy_file_if_newer is deprecated. Use copy_file_if instead."
        )
    )
    return copy_file_if(src_fs, src_path, dst_fs, dst_path, "newer")


def copy_file_if(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
    condition,  # type: Text
):
    # type: (...) -> bool
    """Copy a file from one filesystem to another, depending on a condition.

    Depending on the value of ``strategy``, certain conditions must be fulfilled
    for a file to be copied to ``dst_fs``. The following values
    are supported:

    ``"always"``
        The source file is always copied.
    ``"newer"``
        The last modification time of the source file must be newer than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"older"``
        The last modification time of the source file must be older than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"exists"``
        The source file is only copied if a file of the same path already exists in ``dst_fs``.
    ``"not_exists"``
        The source file is only copied if no file of the same path already exists in ``dst_fs``.


    Arguments:
        src_fs (FS or str): Source filesystem (instance or URL).
        src_path (str): Path to a file on the source filesystem.
        dst_fs (FS or str): Destination filesystem (instance or URL).
        dst_path (str): Path to a file on the destination filesystem.
        condition (str): Name of the condition to check for each file.

    Returns:
        bool: `True` if the file copy was executed, `False` otherwise.

    """
    with manage_fs(src_fs, writeable=False) as _src_fs:
        with manage_fs(dst_fs, create=True) as _dst_fs:
            do_copy = _copy_is_necessary(
                _src_fs, src_path, _dst_fs, dst_path, condition
            )
            if do_copy:
                copy_file_internal(_src_fs, src_path, _dst_fs, dst_path, True)
            return do_copy


def copy_file_internal(
    src_fs,  # type: FS
    src_path,  # type: Text
    dst_fs,  # type: FS
    dst_path,  # type: Text
    lock=False,  # type: bool
):
    # type: (...) -> None
    """Copy a file at low level, without calling `manage_fs` or locking.

    If the destination exists, and is a file, it will be first truncated.

    This method exists to optimize copying in loops. In general you
    should prefer `copy_file`.

    Arguments:
        src_fs (FS): Source filesystem.
        src_path (str): Path to a file on the source filesystem.
        dst_fs (FS): Destination filesystem.
        dst_path (str): Path to a file on the destination filesystem.
        lock (bool): Lock both filesystems before copying.

    """
    if src_fs is dst_fs:
        # Same filesystem, so we can do a potentially optimized
        # copy
        src_fs.copy(src_path, dst_path, overwrite=True)
        return

    def _copy_locked():
        if dst_fs.hassyspath(dst_path):
            with dst_fs.openbin(dst_path, "w") as write_file:
                src_fs.download(src_path, write_file)
        else:
            with src_fs.openbin(src_path) as read_file:
                dst_fs.upload(dst_path, read_file)

    if lock:
        with src_fs.lock(), dst_fs.lock():
            _copy_locked()
    else:
        _copy_locked()


def copy_structure(
    src_fs,  # type: Union[FS, Text]
    dst_fs,  # type: Union[FS, Text]
    walker=None,  # type: Optional[Walker]
    src_root="/",  # type: Text
    dst_root="/",  # type: Text
):
    # type: (...) -> None
    """Copy directories (but not files) from ``src_fs`` to ``dst_fs``.

    Arguments:
        src_fs (FS or str): Source filesystem (instance or URL).
        dst_fs (FS or str): Destination filesystem (instance or URL).
        walker (~fs.walk.Walker, optional): A walker object that will be
            used to scan for files in ``src_fs``. Set this if you only
            want to consider a sub-set of the resources in ``src_fs``.
        src_root (str): Path of the base directory to consider as the root
            of the tree structure to copy.
        dst_root (str): Path to the target root of the tree structure.

    """
    walker = walker or Walker()
    with manage_fs(src_fs) as _src_fs:
        with manage_fs(dst_fs, create=True) as _dst_fs:
            with _src_fs.lock(), _dst_fs.lock():
                _dst_fs.makedirs(dst_root, recreate=True)
                for dir_path in walker.dirs(_src_fs, src_root):
                    _dst_fs.makedir(
                        combine(dst_root, frombase(src_root, dir_path)), recreate=True
                    )


def copy_dir(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Copy a directory from one filesystem to another.

    Arguments:
        src_fs (FS or str): Source filesystem (instance or URL).
        src_path (str): Path to a directory on the source filesystem.
        dst_fs (FS or str): Destination filesystem (instance or URL).
        dst_path (str): Path to a directory on the destination filesystem.
        walker (~fs.walk.Walker, optional): A walker object that will be
            used to scan for files in ``src_fs``. Set this if you only
            want to consider a sub-set of the resources in ``src_fs``.
        on_copy (callable, optional):  A function callback called after
            a single file copy is executed. Expected signature is
            ``(src_fs, src_path, dst_fs, dst_path)``.
        workers (int): Use ``worker`` threads to copy data, or ``0`` (default) for
            a single-threaded copy.

    """
    copy_dir_if(src_fs, src_path, dst_fs, dst_path, "always", walker, on_copy, workers)


def copy_dir_if_newer(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Use ``copy_dir_if`` instead."""
    warnings.warn(
        DeprecationWarning("copy_dir_if_newer is deprecated. Use copy_dir_if instead.")
    )
    copy_dir_if(src_fs, src_path, dst_fs, dst_path, "newer", walker, on_copy, workers)


def copy_dir_if(
    src_fs,  # type: Union[FS, Text]
    src_path,  # type: Text
    dst_fs,  # type: Union[FS, Text]
    dst_path,  # type: Text
    condition="always",  # type: Text
    walker=None,  # type: Optional[Walker]
    on_copy=None,  # type: Optional[_OnCopy]
    workers=0,  # type: int
):
    # type: (...) -> None
    """Copy a directory from one filesystem to another, depending on a condition.

    Depending on the value of ``strategy``, certain conditions must be
    fulfilled for a file to be copied to ``dst_fs``. The following values
    are supported:

    ``"always"``
        The source file is always copied.
    ``"newer"``
        The last modification time of the source file must be newer than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"older"``
        The last modification time of the source file must be older than that of the destination file.
        If either file has no modification time, the copy is performed always.
    ``"exists"``
        The source file is only copied if a file of the same path already exists in ``dst_fs``.
    ``"not_exists"``
        The source file is only copied if no file of the same path already exists in ``dst_fs``.

    Arguments:
        src_fs (FS or str): Source filesystem (instance or URL).
        src_path (str): Path to a directory on the source filesystem.
        dst_fs (FS or str): Destination filesystem (instance or URL).
        dst_path (str): Path to a directory on the destination filesystem.
            condition (str): Name of the condition to check for each file.
            walker (~fs.walk.Walker, optional): A walker object that will be
                used to scan for files in ``src_fs``. Set this if you only want
                to consider a sub-set of the resources in ``src_fs``.
            on_copy (callable):A function callback called after a single file copy
                is executed. Expected signature is ``(src_fs, src_path, dst_fs,
                dst_path)``.
            workers (int): Use ``worker`` threads to copy data, or ``0`` (default) for
                a single-threaded copy.

    """
    on_copy = on_copy or (lambda *args: None)
    walker = walker or Walker()
    _src_path = abspath(normpath(src_path))
    _dst_path = abspath(normpath(dst_path))

    from ._bulk import Copier

    copy_structure(src_fs, dst_fs, walker, src_path, dst_path)

    with manage_fs(src_fs, writeable=False) as _src_fs, manage_fs(
        dst_fs, create=True
    ) as _dst_fs:
        with _src_fs.lock(), _dst_fs.lock():
            _thread_safe = is_thread_safe(_src_fs, _dst_fs)
            with Copier(num_workers=workers if _thread_safe else 0) as copier:
                for dir_path in walker.files(_src_fs, _src_path):
                    copy_path = combine(_dst_path, frombase(_src_path, dir_path))
                    if _copy_is_necessary(
                        _src_fs, dir_path, _dst_fs, copy_path, condition
                    ):
                        copier.copy(_src_fs, dir_path, _dst_fs, copy_path)
                        on_copy(_src_fs, dir_path, _dst_fs, copy_path)


def _copy_is_necessary(
    src_fs,  # type: FS
    src_path,  # type: Text
    dst_fs,  # type: FS
    dst_path,  # type: Text
    condition,  # type: Text
):
    # type: (...) -> bool

    if condition == "always":
        return True

    elif condition == "newer":
        try:
            namespace = ("details", "modified")
            src_modified = src_fs.getinfo(src_path, namespace).modified
            dst_modified = dst_fs.getinfo(dst_path, namespace).modified
        except ResourceNotFound:
            return True
        else:
            return (
                src_modified is None
                or dst_modified is None
                or src_modified > dst_modified
            )

    elif condition == "older":
        try:
            namespace = ("details", "modified")
            src_modified = src_fs.getinfo(src_path, namespace).modified
            dst_modified = dst_fs.getinfo(dst_path, namespace).modified
        except ResourceNotFound:
            return True
        else:
            return (
                src_modified is None
                or dst_modified is None
                or src_modified < dst_modified
            )

    elif condition == "exists":
        return dst_fs.exists(dst_path)

    elif condition == "not_exists":
        return not dst_fs.exists(dst_path)

    else:
        raise ValueError("{} is not a valid copy condition.".format(condition))
