# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

r"""Data structures representing Mozilla's source tree.

The frontend files are parsed into static data structures. These data
structures are defined in this module.

All data structures of interest are children of the TreeMetadata class.

Logic for populating these data structures is not defined in this class.
Instead, what we have here are dumb container classes. The emitter module
contains the code for converting executed mozbuild files into these data
structures.
"""

from __future__ import unicode_literals

import os

from collections import OrderedDict
from mozbuild.util import (
    shell_quote,
    StrictOrderingOnAppendList,
)
import mozpack.path as mozpath
from .sandbox_symbols import FinalTargetValue


class TreeMetadata(object):
    """Base class for all data being captured."""

    def __init__(self):
        self._ack = False

    def ack(self):
        self._ack = True


class ReaderSummary(TreeMetadata):
    """A summary of what the reader did."""

    def __init__(self, total_file_count, total_sandbox_execution_time,
        total_emitter_execution_time):
        TreeMetadata.__init__(self)
        self.total_file_count = total_file_count
        self.total_sandbox_execution_time = total_sandbox_execution_time
        self.total_emitter_execution_time = total_emitter_execution_time


class SandboxDerived(TreeMetadata):
    """Build object derived from a single MozbuildSandbox instance.

    It holds fields common to all sandboxes. This class is likely never
    instantiated directly but is instead derived from.
    """

    __slots__ = (
        'objdir',
        'relativedir',
        'sandbox_all_paths',
        'sandbox_path',
        'srcdir',
        'topobjdir',
        'topsrcdir',
    )

    def __init__(self, sandbox):
        TreeMetadata.__init__(self)

        # Capture the files that were evaluated to build this sandbox.
        self.sandbox_main_path = sandbox.main_path
        self.sandbox_all_paths = sandbox.all_paths

        # Basic directory state.
        self.topsrcdir = sandbox['TOPSRCDIR']
        self.topobjdir = sandbox['TOPOBJDIR']

        self.relativedir = sandbox['RELATIVEDIR']
        self.srcdir = sandbox['SRCDIR']
        self.objdir = sandbox['OBJDIR']

        self.config = sandbox.config

    @property
    def relobjdir(self):
        return mozpath.relpath(self.objdir, self.topobjdir)


class DirectoryTraversal(SandboxDerived):
    """Describes how directory traversal for building should work.

    This build object is likely only of interest to the recursive make backend.
    Other build backends should (ideally) not attempt to mimic the behavior of
    the recursive make backend. The only reason this exists is to support the
    existing recursive make backend while the transition to mozbuild frontend
    files is complete and we move to a more optimal build backend.

    Fields in this class correspond to similarly named variables in the
    frontend files.
    """
    __slots__ = (
        'dirs',
        'parallel_dirs',
        'tool_dirs',
        'test_dirs',
        'test_tool_dirs',
        'tier_dirs',
        'tier_static_dirs',
    )

    def __init__(self, sandbox):
        SandboxDerived.__init__(self, sandbox)

        self.dirs = []
        self.parallel_dirs = []
        self.tool_dirs = []
        self.test_dirs = []
        self.test_tool_dirs = []
        self.tier_dirs = OrderedDict()
        self.tier_static_dirs = OrderedDict()


class BaseConfigSubstitution(SandboxDerived):
    """Base class describing autogenerated files as part of config.status."""

    __slots__ = (
        'input_path',
        'output_path',
        'relpath',
    )

    def __init__(self, sandbox):
        SandboxDerived.__init__(self, sandbox)

        self.input_path = None
        self.output_path = None
        self.relpath = None


class ConfigFileSubstitution(BaseConfigSubstitution):
    """Describes a config file that will be generated using substitutions."""


class HeaderFileSubstitution(BaseConfigSubstitution):
    """Describes a header file that will be generated using substitutions."""


class VariablePassthru(SandboxDerived):
    """A dict of variables to pass through to backend.mk unaltered.

    The purpose of this object is to facilitate rapid transitioning of
    variables from Makefile.in to moz.build. In the ideal world, this class
    does not exist and every variable has a richer class representing it.
    As long as we rely on this class, we lose the ability to have flexibility
    in our build backends since we will continue to be tied to our rules.mk.
    """
    __slots__ = ('variables')

    def __init__(self, sandbox):
        SandboxDerived.__init__(self, sandbox)
        self.variables = {}

class XPIDLFile(SandboxDerived):
    """Describes an XPIDL file to be compiled."""

    __slots__ = (
        'basename',
        'source_path',
    )

    def __init__(self, sandbox, source, module):
        SandboxDerived.__init__(self, sandbox)

        self.source_path = source
        self.basename = mozpath.basename(source)
        self.module = module

class Defines(SandboxDerived):
    """Sandbox container object for DEFINES, which is an OrderedDict.
    """
    __slots__ = ('defines')

    def __init__(self, sandbox, defines):
        SandboxDerived.__init__(self, sandbox)
        self.defines = defines

    def get_defines(self):
        for define, value in self.defines.iteritems():
            if value is True:
                yield('-D%s' % define)
            elif value is False:
                yield('-U%s' % define)
            else:
                yield('-D%s=%s' % (define, shell_quote(value)))

class Exports(SandboxDerived):
    """Sandbox container object for EXPORTS, which is a HierarchicalStringList.

    We need an object derived from SandboxDerived for use in the backend, so
    this object fills that role. It just has a reference to the underlying
    HierarchicalStringList, which is created when parsing EXPORTS.
    """
    __slots__ = ('exports', 'dist_install')

    def __init__(self, sandbox, exports, dist_install=True):
        SandboxDerived.__init__(self, sandbox)
        self.exports = exports
        self.dist_install = dist_install

class Resources(SandboxDerived):
    """Sandbox container object for RESOURCE_FILES, which is a HierarchicalStringList,
    with an extra ``.preprocess`` property on each entry.

    The local defines plus anything in ACDEFINES are stored in ``defines`` as a
    dictionary, for any files that need preprocessing.
    """
    __slots__ = ('resources', 'defines')

    def __init__(self, sandbox, resources, defines=None):
        SandboxDerived.__init__(self, sandbox)
        self.resources = resources
        defs = {}
        defs.update(sandbox.config.defines)
        if defines:
            defs.update(defines)
        self.defines = defs


class IPDLFile(SandboxDerived):
    """Describes an individual .ipdl source file."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class WebIDLFile(SandboxDerived):
    """Describes an individual .webidl source file."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class GeneratedEventWebIDLFile(SandboxDerived):
    """Describes an individual .webidl source file."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class TestWebIDLFile(SandboxDerived):
    """Describes an individual test-only .webidl source file."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class PreprocessedTestWebIDLFile(SandboxDerived):
    """Describes an individual test-only .webidl source file that requires
    preprocessing."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class PreprocessedWebIDLFile(SandboxDerived):
    """Describes an individual .webidl source file that requires preprocessing."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path

class GeneratedWebIDLFile(SandboxDerived):
    """Describes an individual .webidl source file that is generated from
    build rules."""

    __slots__ = (
        'basename',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.basename = path


class ExampleWebIDLInterface(SandboxDerived):
    """An individual WebIDL interface to generate."""

    __slots__ = (
        'name',
    )

    def __init__(self, sandbox, name):
        SandboxDerived.__init__(self, sandbox)

        self.name = name


class LinkageWrongKindError(Exception):
    """Error thrown when trying to link objects of the wrong kind"""


class Linkable(SandboxDerived):
    """Generic sandbox container object for programs and libraries"""
    __slots__ = ('linked_libraries')

    def __init__(self, sandbox):
        SandboxDerived.__init__(self, sandbox)
        self.linked_libraries = []

    def link_library(self, obj):
        assert isinstance(obj, BaseLibrary)
        if isinstance(obj, SharedLibrary) and obj.variant == obj.COMPONENT:
            raise LinkageWrongKindError(
                'Linkable.link_library() does not take components.')
        if obj.KIND != self.KIND:
            raise LinkageWrongKindError('%s != %s' % (obj.KIND, self.KIND))
        self.linked_libraries.append(obj)
        obj.refcount += 1


class BaseProgram(Linkable):
    """Sandbox container object for programs, which is a unicode string.

    This class handles automatically appending a binary suffix to the program
    name.
    If the suffix is not defined, the program name is unchanged.
    Otherwise, if the program name ends with the given suffix, it is unchanged
    Otherwise, the suffix is appended to the program name.
    """
    __slots__ = ('program')

    def __init__(self, sandbox, program):
        Linkable.__init__(self, sandbox)

        bin_suffix = sandbox['CONFIG'].get(self.SUFFIX_VAR, '')
        if not program.endswith(bin_suffix):
            program += bin_suffix
        self.program = program


class Program(BaseProgram):
    """Sandbox container object for PROGRAM"""
    SUFFIX_VAR = 'BIN_SUFFIX'
    KIND = 'target'


class HostProgram(BaseProgram):
    """Sandbox container object for HOST_PROGRAM"""
    SUFFIX_VAR = 'HOST_BIN_SUFFIX'
    KIND = 'host'


class SimpleProgram(BaseProgram):
    """Sandbox container object for each program in SIMPLE_PROGRAMS"""
    SUFFIX_VAR = 'BIN_SUFFIX'
    KIND = 'target'


class HostSimpleProgram(BaseProgram):
    """Sandbox container object for each program in HOST_SIMPLE_PROGRAMS"""
    SUFFIX_VAR = 'HOST_BIN_SUFFIX'
    KIND = 'host'


class BaseLibrary(Linkable):
    """Generic sandbox container object for libraries."""
    __slots__ = (
        'basename',
        'lib_name',
        'import_name',
        'refcount',
    )

    def __init__(self, sandbox, basename):
        Linkable.__init__(self, sandbox)

        self.basename = self.lib_name = basename
        if self.lib_name:
            self.lib_name = '%s%s%s' % (
                sandbox.config.lib_prefix,
                self.lib_name,
                sandbox.config.lib_suffix
            )
            self.import_name = self.lib_name

        self.refcount = 0


class Library(BaseLibrary):
    """Sandbox container object for a library"""
    KIND = 'target'
    __slots__ = (
        'is_sdk',
    )

    def __init__(self, sandbox, basename, real_name=None, is_sdk=False):
        BaseLibrary.__init__(self, sandbox, real_name or basename)
        self.basename = basename
        self.is_sdk = is_sdk


class StaticLibrary(Library):
    """Sandbox container object for a static library"""
    __slots__ = (
        'link_into',
    )

    def __init__(self, sandbox, basename, real_name=None, is_sdk=False,
        link_into=None):
        Library.__init__(self, sandbox, basename, real_name, is_sdk)
        self.link_into = link_into


class SharedLibrary(Library):
    """Sandbox container object for a shared library"""
    __slots__ = (
        'soname',
        'variant',
    )

    FRAMEWORK = 1
    COMPONENT = 2
    MAX_VARIANT = 3

    def __init__(self, sandbox, basename, real_name=None, is_sdk=False,
            soname=None, variant=None):
        assert(variant in range(1, self.MAX_VARIANT) or variant is None)
        Library.__init__(self, sandbox, basename, real_name, is_sdk)
        self.variant = variant
        self.lib_name = real_name or basename
        assert self.lib_name

        if variant == self.FRAMEWORK:
            self.import_name = self.lib_name
        else:
            self.import_name = '%s%s%s' % (
                sandbox.config.import_prefix,
                self.lib_name,
                sandbox.config.import_suffix,
            )
            self.lib_name = '%s%s%s' % (
                sandbox.config.dll_prefix,
                self.lib_name,
                sandbox.config.dll_suffix,
            )
        if soname:
            self.soname = '%s%s%s' % (
                sandbox.config.dll_prefix,
                soname,
                sandbox.config.dll_suffix,
            )
        else:
            self.soname = self.lib_name


class HostLibrary(BaseLibrary):
    """Sandbox container object for a host library"""
    KIND = 'host'


class TestManifest(SandboxDerived):
    """Represents a manifest file containing information about tests."""

    __slots__ = (
        # The type of test manifest this is.
        'flavor',

        # Maps source filename to destination filename. The destination
        # path is relative from the tests root directory. Values are 2-tuples
        # of (destpath, is_test_file) where the 2nd item is True if this
        # item represents a test file (versus a support file).
        'installs',

        # A list of pattern matching installs to perform. Entries are
        # (base, pattern, dest).
        'pattern_installs',

        # Where all files for this manifest flavor are installed in the unified
        # test package directory.
        'install_prefix',

        # Set of files provided by an external mechanism.
        'external_installs',

        # The full path of this manifest file.
        'path',

        # The directory where this manifest is defined.
        'directory',

        # The parsed manifestparser.TestManifest instance.
        'manifest',

        # List of tests. Each element is a dict of metadata.
        'tests',

        # The relative path of the parsed manifest within the srcdir.
        'manifest_relpath',

        # The relative path of the parsed manifest within the objdir.
        'manifest_obj_relpath',

        # If this manifest is a duplicate of another one, this is the
        # manifestparser.TestManifest of the other one.
        'dupe_manifest',
    )

    def __init__(self, sandbox, path, manifest, flavor=None,
            install_prefix=None, relpath=None, dupe_manifest=False):
        SandboxDerived.__init__(self, sandbox)

        self.path = path
        self.directory = mozpath.dirname(path)
        self.manifest = manifest
        self.flavor = flavor
        self.install_prefix = install_prefix
        self.manifest_relpath = relpath
        self.manifest_obj_relpath = relpath
        self.dupe_manifest = dupe_manifest
        self.installs = {}
        self.pattern_installs = []
        self.tests = []
        self.external_installs = set()


class LocalInclude(SandboxDerived):
    """Describes an individual local include path."""

    __slots__ = (
        'path',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.path = path

class GeneratedInclude(SandboxDerived):
    """Describes an individual generated include path."""

    __slots__ = (
        'path',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.path = path


class PerSourceFlag(SandboxDerived):
    """Describes compiler flags specified for individual source files."""

    __slots__ = (
        'file_name',
        'flags',
    )

    def __init__(self, sandbox, file_name, flags):
        SandboxDerived.__init__(self, sandbox)

        self.file_name = file_name
        self.flags = flags


class JARManifest(SandboxDerived):
    """Describes an individual JAR manifest file and how to process it.

    This class isn't very useful for optimizing backends yet because we don't
    capture defines. We can't capture defines safely until all of them are
    defined in moz.build and not Makefile.in files.
    """
    __slots__ = (
        'path',
    )

    def __init__(self, sandbox, path):
        SandboxDerived.__init__(self, sandbox)

        self.path = path


class JavaScriptModules(SandboxDerived):
    """Describes a JavaScript module."""

    __slots__ = (
        'modules',
        'flavor',
    )

    def __init__(self, sandbox, modules, flavor):
        super(JavaScriptModules, self).__init__(sandbox)

        self.modules = modules
        self.flavor = flavor


class SandboxWrapped(SandboxDerived):
    """Generic sandbox container object for a wrapped rich object.

    Use this wrapper class to shuttle a rich build system object
    completely defined in moz.build files through the tree metadata
    emitter to the build backend for processing as-is.
    """

    __slots__ = (
        'wrapped',
    )

    def __init__(self, sandbox, wrapped):
        SandboxDerived.__init__(self, sandbox)

        self.wrapped = wrapped


class JavaJarData(object):
    """Represents a Java JAR file.

    A Java JAR has the following members:
        * sources - strictly ordered list of input java sources
        * generated_sources - strictly ordered list of generated input
          java sources
        * extra_jars - list of JAR file dependencies to include on the
          javac compiler classpath
        * javac_flags - list containing extra flags passed to the
          javac compiler
    """

    __slots__ = (
        'name',
        'sources',
        'generated_sources',
        'extra_jars',
        'javac_flags',
    )

    def __init__(self, name, sources=[], generated_sources=[],
            extra_jars=[], javac_flags=[]):
        self.name = name
        self.sources = StrictOrderingOnAppendList(sources)
        self.generated_sources = StrictOrderingOnAppendList(generated_sources)
        self.extra_jars = list(extra_jars)
        self.javac_flags = list(javac_flags)


class InstallationTarget(SandboxDerived):
    """Describes the rules that affect where files get installed to."""

    __slots__ = (
        'xpiname',
        'subdir',
        'target',
        'enabled'
    )

    def __init__(self, sandbox):
        SandboxDerived.__init__(self, sandbox)

        self.xpiname = sandbox.get('XPI_NAME', '')
        self.subdir = sandbox.get('DIST_SUBDIR', '')
        self.target = sandbox['FINAL_TARGET']
        self.enabled = not sandbox.get('NO_DIST_INSTALL', False)

    def is_custom(self):
        """Returns whether or not the target is not derived from the default
        given xpiname and subdir."""

        return FinalTargetValue(dict(
            XPI_NAME=self.xpiname,
            DIST_SUBDIR=self.subdir)) == self.target


class ClassPathEntry(object):
    """Represents a classpathentry in an Android Eclipse project."""

    __slots__ = (
        'dstdir',
        'srcdir',
        'path',
        'exclude_patterns',
        'ignore_warnings',
    )

    def __init__(self):
        self.dstdir = None
        self.srcdir = None
        self.path = None
        self.exclude_patterns = []
        self.ignore_warnings = False


class AndroidEclipseProjectData(object):
    """Represents an Android Eclipse project."""

    __slots__ = (
        'name',
        'package_name',
        'is_library',
        'res',
        'assets',
        'libs',
        'manifest',
        'recursive_make_targets',
        'extra_jars',
        'included_projects',
        'referenced_projects',
        '_classpathentries',
        'filtered_resources',
    )

    def __init__(self, name):
        self.name = name
        self.is_library = False
        self.manifest = None
        self.res = None
        self.assets = None
        self.libs = []
        self.recursive_make_targets = []
        self.extra_jars = []
        self.included_projects = []
        self.referenced_projects = []
        self._classpathentries = []
        self.filtered_resources = []

    def add_classpathentry(self, path, srcdir, dstdir, exclude_patterns=[], ignore_warnings=False):
        cpe = ClassPathEntry()
        cpe.srcdir = srcdir
        cpe.dstdir = dstdir
        cpe.path = path
        cpe.exclude_patterns = list(exclude_patterns)
        cpe.ignore_warnings = ignore_warnings
        self._classpathentries.append(cpe)
        return cpe
