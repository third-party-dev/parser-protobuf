- Eagerly tokenize: `input -> lexer -> all tokens -> parser`
- Conflated use of EOF:
  - buffer empty
  - end of document
  - Should be "need more input"
- recusive descent assumes completion?
- parser generators optimize for finality
  - token stream is finite and complete
  - validation built around accept/reject
- conflate errors
  - malformed and incomplete become invalid
- ~~lookahead~~ lookback in streaming

Streaming Parsers must:
- chunkboundaries
- partial UTF sequences
- split tokens
- resumable parse stacks
- provisional EOF

Parser categories:
- state machine parser - maintains parse state
- incremental parser - reuses prior parse work
- streaming parser - can suspend/resume on partial input
- resumable lexer - handles split tokens/chunks
- prefix valid parser - distinguishes incomplete vs invalid


Documentation on parsers is mostly junior: What is a parser?


