Just In Time Parsing / Parse On Access

The idea is that as we dereference into a file, we can provide only the top level structure of the data. As we drill down, we're only parsing that path into the file. Each "entry point" to decend into the file structure is a temporal cursor into the Very Large File. If there is no reference to the cursor, it should be deallocated.

To further promote small memory footprint, the framework should use asyncio to handle the JIT reading of data from a single file descriptor (that can seek). In Linux, all page caches are shared so there is not advantage to having multiple file descriptors (so long as there is no lock contention via async and we store our own cursors to seek with on reads.)

Misc Commands:

```sh
sudo apt-get install protobuf-compiler
protoc --descriptor_set_out=descriptor.pb myfile.proto
```

Todos:

- Python testing (i.e. pytest) ... primarily to prevent regressions.
  - Testing partial parsing
  - Testing complete parsing
  - Testing very large parsing.
- Python logging (i.e. import logging).
- Document the common pparse API and end-to-end flow.

- Handle folder paths in Data
- Handle Sharding
- Handle Tensor to Numpy
- Common Tensor object
- Schemes for lazy loading

Considerations:

- Document parsing pickle.
- Very large data, multiple levels deep.
  - Can we have a point path that allows on demand drilling down multiple extractions to the data we want without re-parsing everything from top to position?
  - Need moderate integrity verification (i.e. digesting extractions).
- Streaming data?
- AsyncIO?


Thoughts on Multi-Level Drilling

- Assumed impossible with encryption.
- Compression and other encodings (e.g. base64) may be doable if we track atomic units with inner/outer offsets.
- What demarcations in a compression stream can be reused?
  - Specifically target (in order): zip, gz, xz/lzma, bz2
  - Must also track indices and tables for decompression.

When we do a multi-level drill, we'll likely only have the parser specific Node from the Node tree. We need a path of Extractions to dereference the Node. Perhaps a "Node Of Interest" (NOI) keeps a reference to its source Extraction. All Extraction objects are always kept in memory with their relationships, but we wipe or clear the parsing results. Only "Nodes of interest" (NOI) and their ancestry are kept in memory.

When a complete VLF has been scanned, all Extraction references and Unloaded NOIs are what is left. Any further dereferences will require re-initializing the parser from the off of the immediate Extraction. And to get to that immediate extraction, a recursive opening of Extractions may be required.

Thoughts on folders in Data

Data has been designed as a "read offset get data" object. Extractions read the data and generate child Extractions. If we created a DataFolder subclass, there are several schemes to consider:

- Do the results turn into another Node tree?
- Do we keep a flat list of all recursive files as Extractions? (leaning this way)
- Data is no longer the single source of bytes. We need to create new Data objects for extractions with their own offsets. Each new Data object represents a new file descriptor.
- Potential Data class types: DataFolder, DataFile, DataStream/DataSocket

Because we work in a file system, we need to consider that we may access data as a file of bytes, a stream of bytes (pipe/socket/device), or a list of files. There could theoretically be others that are protocol based (e.g. RemoteExtraction). The two primary for all my current use cases should be encompassed by BytesExtraction, FolderExtraction:

- BytesExtraction is based on Data.
- FolderExtraction does not use Data.
  - Uses path or scope.
  - Keeps list of things in path or scope.
  - May have number of filter types or lazy schemes.



## Resources

- https://www.geeksforgeeks.org/deep-learning/sparse-autoencoders-in-deep-learning/
- https://archive.org/details/youtube-OFS90-FX6pg
- https://www.youtube.com/@ArtOfTheProblem
- https://www.youtube.com/@vcubingx
- https://www.youtube.com/watch?v=kCc8FmEb1nY
- https://transformer-circuits.pub/2021/framework/index.html
- http://neuralnetworksanddeeplearning.com/
- https://michaelnotebook.com/ongoing/llm_uses.html