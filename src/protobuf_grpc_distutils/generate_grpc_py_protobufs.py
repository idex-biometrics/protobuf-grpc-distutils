# Copyright IDEX Biometrics
# Licensed under the MIT License, see LICENSE
# SPDX-License-Identifier: MIT

import setuptools
import os
import glob
from pathlib import Path
from subprocess import check_output, CalledProcessError
from distutils.errors import DistutilsOptionError, DistutilsExecError

class generate_grpc_py_protobufs(setuptools.Command):
    """ Generates the Python *pb2.py and *pb2_grpc.py outputs from a .proto file.

    This class is based directly upon protobuf_distutils as distributed with protocolbuffers,
    https://github.com/protocolbuffers/protobuf/tree/main/python/protobuf_distutils, modified 
    to also output the gRPC classes.

    """
    user_options = [
        ('source_dir', None, 'This is the directory holding .proto files to be processed'),
        ('proto_root_path', None, 'This is the root path for resolving imports in source .proto files'),
        ('extra-proto-paths=', None, 'Specifies additional paths that should be used to find imports, in addition to source_dir'),
        ('output_dir', None, 'Specifies where generated code should be placed'),
        ('proto_files', None, 'A list of strings, specific .proto file paths for generating code, instead of searching for all .proto files under source_path'),
    ]
    boolean_options = ['recurse']

    def initialize_options(self) -> None:  
        self.source_dir = None
        self.proto_root_path = None
        self.extra_proto_paths = []
        self.output_dir = '.'
        self.proto_files = None
        self.recurse = True

    def finalize_options(self) -> None:
        self.ensure_dirname('source_dir')
        self.ensure_string_list('extra_proto_paths')

        if self.output_dir is None:
            self.output_dir = '.'
        self.ensure_dirname('output_dir')

        # SUBTLE: if 'source_dir' is a subdirectory of any entry in
        # 'extra_proto_paths', then in general, the shortest --proto_path prefix
        # (and the longest relative .proto filenames) must be used for
        # correctness. For example, consider:
        #
        #     source_dir = 'a/b/c'
        #     extra_proto_paths = ['a/b', 'x/y']
        #
        # In this case, we must ensure that a/b/c/d/foo.proto resolves
        # canonically as c/d/foo.proto, not just d/foo.proto. Otherwise, this
        # import:
        #
        #     import "c/d/foo.proto";
        #
        # would result in different FileDescriptor.name keys from "d/foo.proto".
        # That will cause all the definitions in the file to be flagged as
        # duplicates, with an error similar to:
        #
        #     c/d/foo.proto: "packagename.MessageName" is already defined in file "d/foo.proto"
        #
        # For paths in self.proto_files, we transform them to be relative to
        # self.proto_root_path, which may be different from self.source_dir.
        #
        # Although the order of --proto_paths is significant, shadowed filenames
        # are errors: if 'a/b/c.proto' resolves to different files under two
        # different --proto_path arguments, then the path is rejected as an
        # error. (Implementation note: this is enforced in protoc's
        # DiskSourceTree class.)

        if self.proto_root_path is None:
            self.proto_root_path = os.path.normpath(self.source_dir)
            for root_candidate in self.extra_proto_paths:
                root_candidate = os.path.normpath(root_candidate)
                if self.proto_root_path.startswith(root_candidate):
                    self.proto_root_path = root_candidate
            if self.proto_root_path != self.source_dir:
                self.announce('using computed proto_root_path: ' + self.proto_root_path, level=2)

        if not self.source_dir.startswith(self.proto_root_path):
            raise DistutilsOptionError('source_dir ' + self.source_dir +
                                       ' is not under proto_root_path ' + self.proto_root_path)

        if self.proto_files is None:
            files = glob.glob(os.path.join(self.source_dir, '*.proto'))
            if self.recurse:
                files.extend(glob.glob(os.path.join(self.source_dir, '**', '*.proto'), recursive=True))
            self.proto_files = [f.partition(self.proto_root_path + os.path.sep)[-1] for f in files]
            if not self.proto_files:
                raise DistutilsOptionError('no .proto files were found under ' + self.source_dir)

        self.ensure_string_list('proto_files')


    def run(self):
        proto_paths = ['--proto_path=' + self.proto_root_path]
        proto_paths.extend(['--proto_path=' + x for x in self.extra_proto_paths])

        protoc_arguments = [
            '--python_out=' + self.output_dir,
            '--grpc_python_out=' + self.output_dir,
        ] + proto_paths + self.proto_files

        try:
            check_output(['python3', '-m', 'grpc_tools.protoc'] + protoc_arguments, text=True)
        except CalledProcessError as e:
            raise DistutilsExecError('protoc compile failed with: "{e.stderr}"')

        for root, dirs, files in os.walk(self.output_dir):
            if '__init__.py' not in files:
                if any(['pb2' in file for file in files]):
                    print(root)
                    open(os.path.join(root, '__init__.py'), 'a').close()

        # Work around the fact that setuptools doesn't re-look for new packages.
        # See discussion: https://github.com/pypa/setuptools/discussions/3728
        with open('MANIFEST.in', 'w') as manifest:
            manifest.write(f"graft {self.output_dir}")

        # Throw an exception if we detect this is a src-layout
        # REVISIT: is there a setuptools way of getting this info?
        output_path = Path(self.output_dir)
        if len(output_path.parts) > 1:
            if output_path.parts[0] == 'src':
                raise DistutilsExecError('src-layout not supported; setuptools does not index generated protobuf modules')