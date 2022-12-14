# protobuf_grpc_distutils

This package enables gRPC protobuf definitions to be installed via `pip install`.  This project takes
inspiration from [protobuf-distutils](https://github.com/protocolbuffers/protobuf/tree/main/python/protobuf_distutils)
and [protobuf-custom-build](https://github.com/sbrother/protobuf-custom-build).

## Background

When trying to package the auto-generated protobuf Python files, you quickly run into an [issue](https://github.com/protocolbuffers/protobuf/issues/1491)
regarding how the Python modules are imported.  There are various ways to work around the issue as detailed in that thread.  This package assumes that the
proto files are structured in a hierarchy that directly maps to your required Python package hierarchy.  See the example below.

## Usage

In order to use this package, it must be added to the build requirements of your target Python package.  A custom build step can then be added
to auto-generate the protobuf and gRPC Python modules when you `pip install` your package.

The difference to the `protobuf-distutils` package is that instead of looking for the `protoc` compiler, it depends on the `grpcio-tools` 
package which provides `grpc_tools.protoc`.  Otherwise, the same options are passed to the `generate_grpc_py_protobufs` method in your `setup.py`.

```
from setuptools import setup
setup(
    # ...
    name='example_project',

    # Require this package, but only for setup (not installation):
    setup_requires=['protobuf_grpc_distutils'],

    options={
        # See below for details.
        'generate_grpc_py_protobufs': {
            'source_dir':        'path/to/protos',
            'extra_proto_paths': ['path/to/other/project/protos'],
            'output_dir':        'path/to/project/sources',  # default '.'
            'proto_files':       ['relative/path/to/just_this_file.proto'],
        },
    },
)
```

## Example

An example project is provided at https://github.com/idex-biometrics/protobuf-grpc-distutils-example.
