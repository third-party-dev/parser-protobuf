wget https://huggingface.co/openai-community/gpt2/resolve/main/onnx/decoder_model.onnx


Just In Time Parsing / Parse On Access

The idea is that as we dereference into a file, we can provide only the top level structure of the data. As we drill down, we're only parsing that path into the file. Each "entry point" to decend into the file structure is a temporal cursor into the Very Large File. If there is no reference to the cursor, it should be deallocated.

To further promote small memory footprint, the framework should use asyncio to handle the JIT reading of data from a single file descriptor (that can seek). In Linux, all page caches are shared so there is not advantage to having multiple file descriptors (so long as there is no lock contention via async and we store our own cursors to seek with on reads.)

