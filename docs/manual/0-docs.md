# Progressive Parsing

## Purpose

In brief, I wanted a framework for parsing incomplete data. A real world example is that I have a tar.gz that contains a zip file that contains a file I want to extract. Perhaps the files was truncated or corrupted halfway through the tar.gz, cutting part of the zip file off as well. With what data we have left, we should be able to:

1. Decompress the GZ as much as possible. Keeping partial results!
2. Extract as many of the tar entries as possible. Keeping partial or truncated results!
3. Assuming we have some of the zip file, extract as many of the zip entries as possible, independent of the footer index! And keeping partial and truncated results!

I've found that, in practice, parsers are written or generated with the assumption that both the raw data and the parsed data must fit into memory all at once. This is a great model if we're talking about small collections of network packets. But when we want to parse large archives and other binaries, we need to reconsider how we manage the parsed data.

Complimenting the parse-ability of a partial file, pparse also aims to be able to parse very large datasets on consumer level hardware. For example, I want to be able to efficiently parse a 200GB file on a machine with 16GB of space. If you consider, conceptually, a very large file can only ever be truncated in a low memory system, and therefore should match the same model well.

- Assumption: We have enough disk space to hold all of the data we'll be parsing.
- Assumption: None of the data we are parsing will change while parsing.

## Concepts

### Synopsis

- **Data** - File descriptor server.
- **Reader** - API for access data from `Data`
- **Cursor** - `Reader` that only represents offset into `Data`
- **Range** - `Reader` of subset of `Data` data with bounds checking.

- **Extraction** - Data not parsed by `Parser` or data to be parsed by `Parser`.
- **BytesExtraction** - Extraction backed by `Data`
- **FolderExtraction** - Extraction backed by virtual file system scope. (**Not implemented**).
- **Parser** - Base class for `Parser` classes.

- **Node** - Base class for `Parser` result node tree nodes.
- **NodeContext** - Base class for `Node` context references (req'd data during parsing.)

### File Descriptor as Data Server

The fundamental idea is that we want a single file descriptor for a single file. Seeking to different parts of the file and having the raw data available for reading is the job of the Linux kernel's file page cache. We don't want to re-implement this because it is a very mature and rock solid code base. Windows file page cache is trash and I'd advise using a VM or WSL.

Right, so that file descriptor is managed by a `Data` object. The `Data` object is a server of sorts that is the only code allowed (by convention) to access the raw data of the file directly. By design, users will never actually call `Data` directly. Instead, a user will `open()` a `Reader` object from `Data`. Think of the `Reader` as a userspace file descriptor. The `Reader` object is what the user will use to `read()`/`tell()`/`seek()` from `Data`. In summary, files are represented as `Data` objects and access to file data is through `Reader` objects.

Looking at `Reader` a bit more, there are two differents types of `Reader`s. The first is what we call a `Cursor`. The `Cursor` tracks the `Data` object its associated with and the _current_ offset into the raw data. Another type is the `Range` object. The `Range` tracks its own `Cursor` as well as the start offset, end offset, and length of the data relevant to the _range_ of data. One way to look at this is the cursor is a pointer to some location in the `Data` while in contrast the `Range` is a selection of data. When reading from a `Range`, you are restricted to the data between the start offset (inclusive) and end offset (exclusive). The `Cursor` object is limited only by the size of data represented with `Data` (i.e. offset 0 to length of data).

### Parsers and Extractions

The `Data`/`Reader`/`Cursor`/`Range` are objects for accessing the raw data. But we need a way to process the raw data. `Parser` objects are responsible for driving the reading and interpretation of the data read. `Parser`s, by design, parse `Extraction`s. An `Extraction` is a named chunk of data that can or can't be parsed. `Parser` objects decide what they are willing to parse. When they parse an `Extraction` and find data they have choosen not to parse, they can optionally create a child `Extraction` for other parsers to attempt to parse. This operation can continue recursively until there is not more data to process.

For example, with an `Extraction` created from a `Range` of `Data`:

- We can give the `Extraction` an array of `Parser` classes to match the data.
- If the `Parser` thinks it can parse the data, it will process the `Extraction`.
- `Parser` will place parsed results in the `Extraction`'s parser specific result slot.
  - Note: Multiple parsers can parse the same `Extraction` data.
- Embedded data within an `Extraction` becomes a child `Extraction`.

At this point, we can envision an `Extraction` tree from the original example, where a Gz extraction has a Tar extraction child. The Tar extraction then has a Zip extraction child along with extraction children for all other tarball entries. The Zip extraction would then have child extractions for all of its entries.

Example Tree:

  - Gz Extraction
    - Tar Extraction
      - Tar File #1 Extraction
      - Tar File #2 Extraction (Zip File)
        - Zip File #1 Extraction
        - Zip File #2 Extraction
      - Tar File #3 Extraction

Each of the extractions can have its own set of parsers or derive a parser registry from its parent `Extraction`.

### Parser Results

`Extraction`s are the unparsed data that a parser can parse _or_ the embedded data that a parser has found that it is not able to parse. Data that the `Parser` object is able to make sense of is put into an `Extraction` object's parser specific results. The results are intended, by convention, to be a tree of Nodes. Typically these Nodes have a `value` member that is a duck typed array, duck typed map, or duck typed scalar value. The duck typing drastically simplifies the code maintenance.

A node's `value` member can be a specific `UNLOADED_VALUE`. `UNLOADED_VALUE` indicates that the parser is able to parse the data, but has either skipped parsing or unloaded the data to save space. Unloading unused data is a key design of being able to process data that is larger than the system memory. The Node plus a Parser should be able to re-parse (i.e. `load()`) the data back into memory on demand.

`Node` objects are specifically designed to minimize footprint. Most `Node` objects will have a `Reader` (e.g. a `Range`), and a `NodeContext` reference. All of the parser's stateful data is kept in the `NodeContext` object. When a `Node` is no longer being actively processed for parsing, its `NodeContext` is erased to save memory.

We keep the `Node` object as minimal as possible for each `Parser` because there could be many thousands of instances in memory at once. If we know that a subclass of `Node` will only exist a handful of times, more references can be stored within the object without bloating memory. For example, an initial `NodeInit` object that will only ever exists as the _root_ of the node tree can have as many attributes as we need without too much worry.

### Node Linkage Strategies

When designing the node tree, different formats will have different demands, especially during the parsing or scanning phase. If we want to minimize the memory footprint, we should only create strong references to parents and weak references to children in the tree nodes themselves. With downward weak references, the garbage collector will eat up everything we don't have an explicit strong reference to. (For example, we can hold onto a single leaf node we care about to protect it from GC, but all other leaves and intermediate nodes will be freed). If we want to refetch the node after its been freed, we simply re-`load()` it.

There is also the traditional use of strong references everywhere. In this case, we must explicitly design options or scheme for when to skip or release node data we don't need. A couple simple examples might be:

- A table of references that age off.
- A user provided filter to determine what to exclude or include.
- A lazy parser that holds everything forever but only after the first access.


## Generic Parser Patterns

When writing a new parser, because of the iterative nature of pparse, we always start with a state machine design. The state of the state machine is kept in the `NodeContext` object. As the state machine processes different parts of the format, it fills out the node tree in a way that compliments the format. Often this means building a stack based list of nodes that are processed in a depth-first fashion.

All parsers are expected to go through a scanning phase when initially loaded. The intention here is to grab enough of the structure data to give users something to dereference. Ideally this means all of the members of the first level map of the node tree. In the case of length delimited formats like MsgPack and Protobuf, this can be very efficient. For formats like JSON and Pickle, you are forced to traverse the entire format to get the top level map keys, which is not efficient.

TODO: Consider how FlexBuffers will be processed since its encoded from leaf to root.

## Safetensors Format

Safetensors is a uint64_t (8-byte) `header_length`, followed by JSON of `header_length` bytes. The header is a single depth map. The only reserved key name is `__metadata__`. All other key names are the names of the tensors within the safetensors file. Each tensor header contains information about its marshalling and the `data_offsets` of the data from the bottom of the JSON header. In otherwords, `header_length + data_offsets[0] + 8` is the absolute offset into the file for the tensor data.

For usability, a single model serialized into safetensors can be shared across multiple safetensor files. These safetensor files are loosely bound by a index JSON file. The index JSON is a map with 2 keys, `__metadata__` and `weight_map`. The keys within the `weight_map` map are the names of all the tensors managed by the index JSON. The value of each tensor entry is the safetensors file that contains the tensor header and data.

### Parser Implementation

There are 3 parsers involved with parsing safetensors:

- thirdparty.pparse.lazy.safetensors.index.Parser - Parses the index JSON
- thirdparty.pparse.lazy.safetensors.Parser - Parsers a single safetensors file.
- thirdparty.pparse.lazy.json.Parser - Parses the JSON of the index and safetensors.

When parsing the safetensors index, the parser will generate a new `Extraction` child for each unique safetensors files it sees. The parser will then scan each of the safetensors files as children. The safetensors parser will process the JSON header as an additional `Extraction` child of the safetensor `Extraction`.

### Viewer Implementation

By design, only the JSON of the safetensors index and safetensors files are initially processed. The tensor data is only retrieved or loaded by the Viewer object. The viewer object can lists the tensors by name. The user can request a `Tensor` object. The `Tensor` object itself is responsible for loading the tensor data. It can also reference all of the tensor metadata and return the tensor data as a numpy object using `numpy.frombuffer()`.

Note: There is a developing idea of having a generic `Tensor` object across all model parsers that provides, at a minimum, the shape, data type, data, and numpy buffer of any given `Tensor`.

## PyTorch Zip Format

PyTorch Zip Format has a `data.pkl` file that is the index of all the tensor data. The pickle also contains python execution instruction for loading the tensor data into memory. The tensor location is determined by the pickle data, but is often stored in the `data/` folder of the pytorch zip file. Also, the `data.pkl` can be multiple pickle streams (delimited by the `STOP` instruction).

TODO: Consider the tar and other version format coverage.
TODO: Consider TorchScript python code processing:
  - AST for safety & compilation (i.e. torch.jit.script)?
  - Can we use the AST to infer a computational graph?
  - Can we use the TorchScript to get layers and activation?

### Parser Implementation

**Incomplete**

There are at least 2 parsers involved with parsing pytorch files:

- thirdparty.pparse.lazy.zip.Parser - Parses the outer zip file of the PyTorch file.
- thirdparty.pparse.lazy.pickle.Parser - Parses the pickle index file for the PyTorch tensors.

With built-in (safe) pparse pickle parser code, pparse can interpret the entire pickle to get all of the tensor names. Given that pparse understands the dependent calls made by the PyTorch pickle (using conventional pytorch access methods), pparse should also be able to reference and read in the tensor data each tensor entry refers too.

### Viewer Implementation

**Not Started**

The viewer for PyTorch, like other viewers, is able to list the tensor names and generate `Tensor` objects that represent a single tensor. The `Tensor` object will then be responsible for its attributes, shape, data type, data, and numpy object returns.

## Onnx Format

Onnx is a cross platform format that may include an embedded computational graph with the tensor data. It is protobuf based. The protobuf definitions are available on Github. Onnx also has a standard JSON representation. 

Note: PyTorch Onnx export requires tracing and therefore can not guarentee the full computational graph.

### Parser Implementation

The Onnx format is a protobuf based format. Its assumed that the Onnx format will start with `onnx.ModelProto` message format. The pparse Onnx parser is iterative, like the other parsers, but it requires a (compiled) protobuf descriptor file to successfully work its way through the format. The protobuf parser is instantiated in a manner that provides the `onnx.pb` file and the `onnx.ModelProto` as the starting map type when used.

TODO: Use if-utf8-decodable hueristic to guess if a LEN field is a string OR a unknown submessage.
TODO: Skip (and set as UNLOADED_VALUE) for all raw_data entries until referenced.
TODO: Support onnx external data references (required for Onnx files > 2GiB/4GiB)

### View Implementation

**Not Started**

The viewer for Onnx, like other viewers, is able to list the _named_ tensors and generate `Tensor` objects that represent a single tensor. The `Tensor` object will then be responsible for its attributes, shape, data type, data, and numpy object returns. Onnx additionally has many other TensorProto messages that are part of the embedded computational graph and are not named. These are not currently reference-able via the standard `Tensor` object API. Instead, they must be dereferenced explicitly via the Node tree produced by the parser.


## Lessons Learned

While pparse design doesn't intend to change, a lot of simplicity could be applied with additional assumptions. 

## Questions / Considerations

- Are there examples of tensors that themselves are >=2GiB?
- If we assume that all structure data will always fit entirely in memory, many shortcuts could be employed.
- What complexity does multi-level-drill-down imply?
- Can we align a Node to a GZ offset mid-compression stream without knowledge of the previous decompression?
