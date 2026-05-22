#!/usr/bin/env python3

import json
import logging

import thirdparty.pparse.lib as pparse

log = logging.getLogger(__name__)

from thirdparty.pparse.lib import (
    EndOfDataException,
    EndOfNodeException,
    UnsupportedFormatException,
)

from thirdparty.pparse.utils import decode_utf8_partial


# ---- Generic ----

class XmlParsingState(object):
    def parse_data(self, node: pparse.Node):
        raise NotImplementedError()


class XmlParsingComplete(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        parser._end_container_node(node)
        return pparse.ASCEND


# ---- Common ----


class XmlParsingMetaWhitespace(XmlParsingState):
    CHUNK_SIZE = 0x100
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020']

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingMetaWhitespace.CHUNK_SIZE)
        #breakpoint()
        if len(data) == 0:
            # If we're looking at whitespace and we're in root node
            # and we have document, return NEXT
            # TODO: Determine if we're root node and if we have 'document'.
            return pparse.NEXT
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse XML meta whitespace.")

        log.debug(f"XmlParsingWhitespace({id(node):x}) off {ctx.tell()} data {data[:10]}")

        offset = 0
        while offset < len(data):
            if not data[offset : offset + 1] in XmlParsingMetaWhitespace.WHITESPACE:
                break
            offset += 1
        parser.encoded_skip(ctx, data[:offset])

        # Chained state.
        return pparse.NEXT


class XmlParsingEqualSeparator(XmlParsingState):
    WHITESPACE_CHARACTERS = ['\u0009', '\u000a', '\u000d', '\u0020'] # tab, nl, cr, sp

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 1)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse XML attr equal separator.")

        if data[0] == '=':
            parser.encoded_skip(ctx, data[0])
            return pparse.NEXT
        
        breakpoint()
        raise Exception(f"In XmlParsingEqualSeparator, expected '\"', got {data}")


class XmlParsingElementAttrValue(XmlParsingState):
    DELIMITERS = ['\u0009', '\u000a', '\u000d', '\u0020', '\u003d']
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingElementAttrValue.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element attr value.")

        if data[0] == '"' and ctx._cur_attr_name not in node._value['attrib']:
            # Start of the value here.
            node._value['attrib'][ctx._cur_attr_name] = ''

            # Do we have the end of the value too?
            end_quote = data[1:].find('"')
            if end_quote < 0:
                # No end of quote, store what we've got and try again.
                node._value['attrib'][ctx._cur_attr_name] += data[1:]
                parser.encoded_skip(ctx, data)
                return pparse.AGAIN

            if end_quote >= 0:
                # Yes, whole value found in single go.
                node._value['attrib'][ctx._cur_attr_name] += data[1:end_quote+1]
                parser.encoded_skip(ctx, data[:end_quote+2])
                ctx._next_state(XmlParsingElement)
                return pparse.NEXT
        
        elif ctx._cur_attr_name in node._value:
            # Assume we've already seen the start quote.

            # Do we have the end of the value?
            end_quote = data.find('"')
            if end_quote < 0:
                # No end of quote, store what we've got and try again.
                node._value['attrib'][ctx._cur_attr_name] += data
                parser.encoded_skip(ctx, data)
                return pparse.AGAIN

            if end_quote >= 0:
                # Yes, whole value found.
                node._value['attrib'][ctx._cur_attr_name] += data[:end_quote]
                parser.encoded_skip(ctx, data[:end_quote+1])
                ctx._next_state(XmlParsingElement)
                return pparse.NEXT


class XmlParsingElementAttrName(XmlParsingState):
    DELIMITERS = ['\u0009', '\u000a', '\u000d', '\u0020', '\u003d']
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingElementAttrName.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element attribute name.")

        if not hasattr(ctx, '_cur_attr_name'):
            ctx._cur_attr_name = ''

        name_end = next((i for i, c in enumerate(data) if c in XmlParsingElementAttrName.DELIMITERS), -1)
        if name_end < 0:
            ctx._cur_attr_name += data
            parser.encoded_skip(ctx, data)
            return pparse.AGAIN

        ctx._cur_attr_name += data[:name_end]
        parser.encoded_skip(ctx, data[:name_end])
        
        # Chained state.
        return pparse.NEXT


class XmlParsingElementClosingTagEnd(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 1)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse XML element closing tag.")
        
        if data[:1] != '>':
            raise Exception(f"Expected >, got {data[:1]}")
        parser.encoded_skip(ctx, data[:1])
        parser._end_container_node(node)
        return pparse.ASCEND


class XmlParsingElementClosingTag(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020', '\u003e'] # tab, nl, cr, sp, >
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingElementClosingTag.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element closing tag.")

        tag_end = next((i for i, c in enumerate(data) if c in XmlParsingElementClosingTag.WHITESPACE), -1)
        if tag_end < 0:
            parser.encoded_skip(ctx, data[:tag_end])
            return pparse.AGAIN

        parser.encoded_skip(ctx, data[:tag_end])
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingElementClosingTagEnd])
        return pparse.AGAIN


class XmlParsingTextNode(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingTextNode.CHUNK_SIZE)
        if len(data) < 1:
            raise EndOfDataException("Not enough data to parse XML text node.")
        
        if not hasattr(ctx, '_cur_text_node'):
            ctx._cur_text_node = ''

        text_end = data.find('<')
        if text_end < 0:
            ctx._cur_text_node += data
            parser.encoded_skip(ctx, data)
            return pparse.AGAIN
        
        if text_end >= 0:
            ctx._cur_text_node += data[:text_end]
            parser.encoded_skip(ctx, data[:text_end])
            node._value = ctx._cur_text_node
            parser._end_container_node(node)
            return pparse.ASCEND


class XmlParsingElement(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 16)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element open symbol.")

        if data[:2] == '/>':
            # We're done.
            parser.encoded_skip(ctx, data[:2])
            parser._end_container_node(node)
            return pparse.ASCEND
        
        if data[:1] == '>':
            parser.encoded_skip(ctx, data[:1])

            # We're done with attrs, now push down for more content.
            node._value['content'] = parser.new_list_node(node)
            node._value['content'].ctx()._init_state(XmlParsingContent)
            ctx._descendants.append(node._value['content'])

            # When we return, we're done with this element. Keep going up.
            ctx._next_state(XmlParsingComplete)
            return pparse.AGAIN

        ctx._next_states([
            XmlParsingMetaWhitespace,
            XmlParsingElementAttrName,
            XmlParsingMetaWhitespace,
            XmlParsingEqualSeparator,
            XmlParsingMetaWhitespace,
            XmlParsingElementAttrValue,
            XmlParsingMetaWhitespace,
            XmlParsingElement,
        ])
        return pparse.AGAIN


class XmlParsingElementTag(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020', '\u002f', '\u003e'] # tab, nl, cr, sp, /, >
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingElementTag.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element tag.")

        tag_end = next((i for i, c in enumerate(data) if c in XmlParsingElementTag.WHITESPACE), -1)
        if tag_end < 0:
            parser.encoded_skip(ctx, data)
            node._value['tag'] += data
            return pparse.AGAIN

        node._value['tag'] += data[:tag_end]
        parser.encoded_skip(ctx, data[:tag_end])

        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingElement])
        return pparse.AGAIN


class XmlParsingElementStart(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 16)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element open symbol.")

        if data[:1] != '<':
            raise Exception(f"Expected <, got {data[:1]}")
        parser.encoded_skip(ctx, data[:1])

        child_node = parser.new_map_node(node)
        child_node._value['tag'] = ''
        child_node._value['attrib'] = {}

        child_node.ctx()._init_state(XmlParsingElementTag)
        node._value.append(child_node)
        ctx._descendants.append(child_node)

        # Chained state.
        return pparse.NEXT


class XmlParsingCDataStart(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 9)
        if len(data) < 9:
            raise EndOfDataException("Not enough data to parse XML element comment start.")

        if data[:9] == '<![CDATA[':
            parser.encoded_skip(ctx, data[:9])

            # Create node for comment parsing.
            cdata_node = parser.new_data_node(node)
            cdata_node.ctx()._init_state(XmlParsingCData)

            # Add to content tree and schedule for processing
            node._value.append(cdata_node)
            ctx._descendants.append(cdata_node)

            # When we ascend, return to content parsing.
            ctx._next_state(XmlParsingContent)
            return pparse.AGAIN

        raise Exception(f"Expected <![CDATA[, got {data[:4]}")


class XmlParsingCData(XmlParsingState):
    CHUNK_SIZE = 0x100
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingCData.CHUNK_SIZE)
        if len(data) < 3:
            raise EndOfDataException("Not enough data to parse XML comment.")

        if node._value == pparse.UNLOADED_VALUE:
            node._value = ''

        cdata_end = data.find(']]>')
        if cdata_end < 0:
            # Skip last 2 in case they are part of the '-->'
            node._value += data[:-2]
            parser.encoded_skip(data[:-2])
            return pparse.AGAIN

        node._value += data[:cdata_end]
        parser.encoded_skip(ctx, data[:cdata_end+3])
        parser._end_container_node(node)
        return pparse.ASCEND


class XmlParsingCommentStart(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 4)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse XML element comment start.")

        if data[:4] == '<!--':
            parser.encoded_skip(ctx, data[:4])

            # Create node for comment parsing.
            comment_node = parser.new_data_node(node)
            comment_node.ctx()._init_state(XmlParsingComment)

            # Add to content tree and schedule for processing
            #breakpoint()
            node._value.append(comment_node)
            ctx._descendants.append(comment_node)

            # ** Caller must set return state before setting CommentStart
            return pparse.NEXT

        raise Exception(f"Expected <!--, got {data[:4]}")


class XmlParsingComment(XmlParsingState):
    CHUNK_SIZE = 0x100
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingComment.CHUNK_SIZE)
        if len(data) < 3:
            raise EndOfDataException("Not enough data to parse XML comment.")

        if node._value == pparse.UNLOADED_VALUE:
            node._value = ''

        comment_end = data.find('-->')
        if comment_end < 0:
            # Skip last 2 in case they are part of the '-->'
            node._value += data[:-2]
            parser.encoded_skip(data[:-2])
            return pparse.AGAIN

        node._value += data[:comment_end]
        parser.encoded_skip(ctx, data[:comment_end+3])
        parser._end_container_node(node)
        
        return pparse.ASCEND


class XmlParsingProcessorInstructionStart(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, 2)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element comment start.")

        if data[:2] == '<?':
            parser.encoded_skip(ctx, data[:2])

            # Create node for comment parsing.
            instruction_node = parser.new_map_node(node)
            instruction_node._value['target'] = ''
            instruction_node._value['data'] = ''
            instruction_node.ctx()._init_state(XmlParsingProcessorInstructionTarget)

            # Add to content tree and schedule for processing
            node._value.append(instruction_node)
            ctx._descendants.append(instruction_node)

            # Chained state
            return pparse.NEXT

        raise Exception(f"Expected <?, got {data[:2]}")


class XmlParsingProcessorInstructionTarget(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020', '\u003f'] # tab, nl, cr, sp, ?
    CHUNK_SIZE = 0x100
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingProcessorInstructionTarget.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML processor instruction.")

        tag_end = next((i for i, c in enumerate(data) if c in XmlParsingProcessorInstructionTarget.WHITESPACE), -1)
        if tag_end < 0:
            parser.encoded_skip(data)
            node._value['target'] += data
            return pparse.AGAIN

        node._value['target'] += data[:tag_end]
        parser.encoded_skip(ctx, data[:tag_end])

        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingProcessorInstruction])
        return pparse.AGAIN


class XmlParsingProcessorInstruction(XmlParsingState):
    CHUNK_SIZE = 0x100
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingProcessorInstruction.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML processor instruction.")

        instruction_end = data.find('?>')
        if instruction_end < 0:
            # Skip last 1 in case its part of the '?>'
            node._value['data'] += data[:-1]
            parser.encoded_skip(data[:-1])
            return pparse.AGAIN

        node._value['data'] += data[:instruction_end]
        parser.encoded_skip(ctx, data[:instruction_end+2])
        parser._end_container_node(node)
        
        return pparse.ASCEND


# We just saw a '<' in document phase, what do we do?
class XmlParsingContent(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingContent.CHUNK_SIZE)
        if len(data) < 2:

            # If we're the document root, ASCEND.
            if node.ctx() and node.ctx().parent():
                if isinstance(node.ctx().parent()._value, dict):
                    if 'document' in node.ctx().parent()._value:
                        if node.ctx().parent()._value['document'] == node:
                            parser._end_container_node(node)
                            return pparse.ASCEND

            raise EndOfDataException("Not enough data to parse XML element content.")

        if data[:2] == '<!':
            if len(data) >= 4 and data[:4] == '<!--':
                ctx._next_states([XmlParsingCommentStart, XmlParsingContent])
                return pparse.AGAIN

            if len(data) >= 9 and data[:4] == '<![CDATA[':
                ctx._next_state(XmlParsingCDataStart)
                return pparse.AGAIN

            raise EndOfDataException("Not enough data to parse XML markup declaration.")

        if data[:2] == '<?':
            ctx._next_states([XmlParsingProcessorInstructionStart, XmlParsingContent])
            return pparse.AGAIN

        if data[:2] == '</':
            parser.encoded_skip(ctx, data[:2])
            ctx._next_state(XmlParsingElementClosingTag)
            return pparse.AGAIN
        
        if data[:1] == '<':
            #! bug?
            ctx._next_states([XmlParsingElementStart, XmlParsingContent])
            return pparse.AGAIN
        
        # Everything else is a text node child.
        text_node = parser.new_data_node(node)
        text_node.ctx()._init_state(XmlParsingTextNode)
        node._value.append(text_node)
        ctx._descendants.append(text_node)
        return pparse.AGAIN


# If XML Decl exists, continue parsing, otherwise move onto prolog.
class XmlParsingContentStart(XmlParsingState):

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # Assuming we at the starting '<' of the root element.
        parser.encoded_skip(ctx, '<')

        doc_node = parser.new_map_node(node)
        doc_node._value['tag'] = ''
        doc_node._value['attrib'] = {}
        doc_node.ctx()._init_state(XmlParsingElementTag)

        node._value['document'] = doc_node
        ctx._descendants.append(doc_node)

        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingEpilogStart])
        return pparse.AGAIN


# ---- Doctype ----


class XmlParsingDoctype(XmlParsingState):
    # TODO: Implement me!
    def parse_data(self, node: pparse.Node):
        breakpoint()
        parser._end_container_node(node)
        return pparse.ASCEND


# ---- Prolog / Epilog / Encoding ----


# We just saw a '<' in document phase, what do we do?
class XmlParsingEpilog(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingEpilog.CHUNK_SIZE)
        if len(data) < 2:
            # ** Not going to try hard here. There is no clean deterministic way
            # ** to find the end of the stream without guilty knowledge of the
            # ** schema. Epilog is either there or we simply ASCEND and call it
            # ** done.
            return pparse.ASCEND

        if data[:2] == '<!':
            if len(data) >= 4 and data[:4] == '<!--':
                ctx._next_states([XmlParsingCommentStart, XmlParsingEpilog])
                return pparse.AGAIN

            if len(data) >= 9 and data[:9] == '<!DOCTYPE':
                raise Exception("Doctype not supported in epilog.")

            if len(data) >= 9 and data[:4] == '<![CDATA[':
                raise Exception("CDATA not allowed in epilog.")

            raise EndOfDataException("Not enough data to parse XML markup declaration.")

        if data[:2] == '<?':
            ctx._next_states([XmlParsingProcessorInstructionStart, XmlParsingEpilog])
            return pparse.AGAIN

        if data[:2] == '</':
            raise Exception("Found invalid closing tag in epilog.")
        
        if data[:1] == '<':
            raise Exception("Found invalid element start in epilog.")
        
        # Everything else is whitespace.
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingEpilog])
        return pparse.AGAIN


class XmlParsingEpilogStart(XmlParsingState):
    # def parse_data(self, node: pparse.Node):
    #     breakpoint()
    #     print("In epilog")
    #     parser._end_container_node(node)
    #     return pparse.ASCEND
    
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        node._value['epilog'] = parser.new_list_node(node)
        node._value['epilog'].ctx()._init_states([
            XmlParsingMetaWhitespace,
            XmlParsingEpilog,
        ])
        ctx._descendants.append(node._value['epilog'])
        
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingComplete])
        return pparse.AGAIN


class XmlParsingPrologFinish(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # TODO: Do validation and setup for content processing.

        parser._end_container_node(node)
        return pparse.ASCEND


# We just saw a '<' in document phase, what do we do?
class XmlParsingProlog(XmlParsingState):
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingProlog.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML element content.")

        if data[:2] == '<!':
            if len(data) >= 4 and data[:4] == '<!--':
                ctx._next_states([XmlParsingCommentStart, XmlParsingProlog])
                return pparse.AGAIN

            if len(data) >= 9 and data[:9] == '<!DOCTYPE':
                raise Exception("Doctype not yet supported in prolog.")

            if len(data) >= 9 and data[:4] == '<![CDATA[':
                raise Exception("Invalid CDATA found in prolog.")

            raise EndOfDataException("Not enough data to parse XML markup declaration.")

        if data[:2] == '<?':
            ctx._next_states([XmlParsingProcessorInstructionStart, XmlParsingProlog])
            return pparse.AGAIN

        if data[:2] == '</':
            raise Exception("Found invalid closing tag in prolog.")
        
        if data[:1] == '<':
            # Found the end of the prolog.
            ctx._next_state(XmlParsingPrologFinish)
            return pparse.AGAIN
        
        # Everything else is whitespace.
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingProlog])
        return pparse.AGAIN


# If XML Decl exists, continue parsing, otherwise move onto prolog.
class XmlParsingPrologStart(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020']

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        node._value['prolog'] = parser.new_list_node(node)
        node._value['prolog'].ctx()._init_states([
            XmlParsingMetaWhitespace,
            XmlParsingProlog,
        ])
        ctx._descendants.append(node._value['prolog'])
        
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingContentStart])
        return pparse.AGAIN


# Always Whitespace -> Attribute -> Whitespace -> '=' -> Whitespace -> Value
class XmlParsingDeclAttributeName(XmlParsingState):
    DELIMITERS = ['\u0009', '\u000a', '\u000d', '\u0020', '\u003d'] # tab, nl, cr, sp, =
    CHUNK_SIZE = 0x100

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data, bytes_len = parser.decoded_peek(ctx, XmlParsingDeclAttributeName.CHUNK_SIZE)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML attr name.")

        if not hasattr(ctx, '_attr_name_builder'):
            ctx._attr_name_builder = ''
        if not hasattr(ctx, '_cur_attr_name'):
            ctx._cur_attr_name = None

        # Find first index of any character from DELIMITERS or -1 for none (similar to str.find()).
        equal_offset = next((i for i, c in enumerate(data) if c in XmlParsingDeclAttributeName.DELIMITERS), -1)
        #equal_offset = data.find('=')
        if equal_offset < 0:
            ctx._attr_name_builder += data
            parser.encoded_skip(ctx, data)
            return pparse.AGAIN

        ctx._attr_name_builder += data[:equal_offset]
        ctx._cur_attr_name = ctx._attr_name_builder
        del ctx._attr_name_builder
        # Check for duplicates
        if ctx._cur_attr_name in node._value:
            raise Exception(f"Duplicate attribute name found: {ctx._cur_attr_name}")
        parser.encoded_skip(ctx, data[:equal_offset])
        # Chained state.
        return pparse.NEXT


class XmlParsingDeclAttributeValue(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # TODO: Verify _cur_attr_name is set.
        attr_name = getattr(ctx, '_cur_attr_name', None)

        data, bytes_len = parser.decoded_peek(ctx, 0x100)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML attr value.")

        if data[0] == '"' and attr_name not in node._value:
            # Start of the value here.
            node._value[attr_name] = ''

            # Do we have the end of the value too?
            end_quote = data[1:].find('"')
            if end_quote < 0:
                # No end of quote, store what we've got and try again.
                node._value[attr_name] += data[1:]
                parser.encoded_skip(ctx, data)
                return pparse.AGAIN

            if end_quote >= 0:
                # Yes, whole value found in single go.
                node._value[attr_name] += data[1:end_quote+1]
                parser.encoded_skip(ctx, data[:end_quote+2])
                return pparse.NEXT
        
        elif ctx._cur_attr_name in node._value:
            # Assume we've already seen the start quote.

            # Do we have the end of the value?
            end_quote = data.find('"')
            if end_quote < 0:
                # No end of quote, store what we've got and try again.
                node._value[attr_name] += data
                parser.encoded_skip(ctx, data)
                return pparse.AGAIN

            if end_quote >= 0:
                # Yes, whole value found.
                node._value[attr_name] += data[:end_quote]
                parser.encoded_skip(ctx, data[:end_quote+1])
                return pparse.NEXT


# If XML Decl exists, continue parsing, otherwise move onto prolog.
class XmlParsingXmlDeclaration(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020']

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # 6 characters of utf32 is 24 bytes.
        data, bytes_len = parser.decoded_peek(ctx, 6)
        if len(data) < 2:
            raise EndOfDataException("Not enough data to parse XML Declaration meta.")

        # Assuming we're at the end or we're at start of an attribute name.

        if data[:2] == '?>':
            parser.encoded_skip(ctx, data[:2])
            parser._end_container_node(node)
            return pparse.ASCEND
        
        # Iterate through all attributes.
        ctx._next_states([
            XmlParsingDeclAttributeName,
            XmlParsingMetaWhitespace,
            XmlParsingEqualSeparator,
            XmlParsingMetaWhitespace,
            XmlParsingDeclAttributeValue,
            XmlParsingMetaWhitespace,
            XmlParsingXmlDeclaration,
        ])

        return pparse.AGAIN


# If XML Decl exists, continue parsing, otherwise move onto prolog.
class XmlParsingXmlDeclarationStart(XmlParsingState):
    WHITESPACE = ['\u0009', '\u000a', '\u000d', '\u0020']

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # 6 characters of utf32 is 24 bytes.
        data, bytes_len = parser.decoded_peek(ctx, 6)
        if len(data) < 6:
            raise EndOfDataException("Not enough data to parse XML Declaration.")

        if data[:5] == '<?xml' and data[5] in XmlParsingXmlDeclarationStart.WHITESPACE:
            parser.encoded_skip(ctx, data[:5])

            node._value['xml_decl'] = parser.new_map_node(node)
            node._value['xml_decl'].ctx()._init_states([
                XmlParsingMetaWhitespace,
                XmlParsingXmlDeclaration,
            ])
            ctx._descendants.append(node._value['xml_decl'])
        
        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingPrologStart])
        return pparse.AGAIN


class XmlParsingUtf32LittleEndian(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        breakpoint()
        raise Exception("UTF32LE not yet supported.")

        ctx._next_state(XmlParsingXmlDeclaration)
        return pparse.AGAIN


class XmlParsingUtf32BigEndian(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        breakpoint()
        raise Exception("UTF32BE not yet supported.")

        ctx._next_state(XmlParsingXmlDeclaration)
        return pparse.AGAIN


class XmlParsingUtf16LittleEndian(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        breakpoint()
        raise Exception("UTF16LE not yet supported.")

        ctx._next_state(XmlParsingXmlDeclaration)
        return pparse.AGAIN


class XmlParsingUtf16BigEndian(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        breakpoint()
        raise Exception("UTF16BE not yet supported.")

        ctx._next_state(XmlParsingXmlDeclaration)
        return pparse.AGAIN


class XmlParsingUtf8(XmlParsingState):
    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        # This will be final encoding value, but we use bom/assumption for now.
        parser.encoding = "utf-8"
        parser.partial_decode = decode_utf8_partial

        ctx._next_states([XmlParsingMetaWhitespace, XmlParsingXmlDeclarationStart])
        return pparse.AGAIN


class XmlParsingBom(XmlParsingState):
    WHITESPACE_CHARACTERS = ['\x09', '\x0a', '\x0d', '\x20']
    UTF32LE = b'\xff\xf3\x00\x00'
    UTF32BE = b'\x00\x00\xfe\xff'
    UTF16LE = b'\xff\xfe'
    UTF16BE = b'\xfe\xff'
    UTF8 = b'\xef\xbb\xbf'

    def parse_data(self, node: pparse.Node):
        ctx = node.ctx()
        parser = ctx.parser()

        data = ctx.peek(6)
        if len(data) < 4:
            raise EndOfDataException("Not enough data to parse XML BOM.")

        if data[:4] == XmlParsingBom.UTF32LE:
            node._value['bom_encoding'] = "utf-32-le"
            ctx.skip(4)
            ctx._next_state(XmlParsingUtf32LittleEndian)
            return pparse.AGAIN

        elif data[:4] == XmlParsingBom.UTF32BE:
            node._value['bom_encoding'] = "utf-32-be"
            ctx.skip(4)
            ctx._next_state(XmlParsingUtf32BigEndian)
            return pparse.AGAIN

        elif data[:2] == XmlParsingBom.UTF16LE:
            node._value['bom_encoding'] = "utf-16-le"
            ctx.skip(2)
            ctx._next_state(XmlParsingUtf16LittleEndian)
            return pparse.AGAIN

        elif data[:2] == XmlParsingBom.UTF16BE:
            node._value['bom_encoding'] = "utf-16-be"
            ctx.skip(2)
            ctx._next_state(XmlParsingUtf16BigEndian)
            return pparse.AGAIN

        elif data[:3] == XmlParsingBom.UTF8:
            node._value['bom_encoding'] = "utf-8"
            ctx.skip(3)
            ctx._next_state(XmlParsingUtf8)
            return pparse.AGAIN
        
        elif data[:5] == b'<?xml' and chr(data[5]) in XmlParsingBom.WHITESPACE_CHARACTERS:
            # no bom_encoding, assuming Utf8 for XML declaration (if present)
            ctx._next_state(XmlParsingUtf8)
            return pparse.AGAIN

        else:
            # Anything else is assumed Utf8
            # TODO: Consider validating <?xml doesn't show up later.
            ctx._next_state(XmlParsingUtf8)
            return pparse.AGAIN

'''

    ## States

    XmlParsingProlog
    XmlParsingBom
    XmlParsingXmlDeclaration
    XmlParsingDocType

    XmlParsingDocument
    XmlParsingEpilog

    XmlParsingProcessingInstruction
    XmlParsingTextNode
    XmlParsingCData
    XmlParsingValue

    XmlParsingEntity - Note: May change with DocType implementation

    XmlParsingWhitespace - Whitespace between `<`/`>` (everything else is a text node).


    ## Init

    Initial XML State checks BOM and <?xml{WHITESPACE} for encoding. If BOM is UTF16 
    and <?xml and <?xml says not UTF16, bad. If <?xml states utf-8 or something else 
    not in conflict with BOM, assign the partial decoder and move into prolog state.

    ## Phases

    In prolog state, process processor instructions, comments, whitespace (no 
    non-whitespace text), and markup declarations (DOCTYPE, CDATA).

    The first element encountered in prolog triggers descendent into document state
    with the parent node set to epilog state. In the document state, we process 
    start/end/empty tags, character data, comments, processor instructions, 
    CDATA sections, whitespace, and entity references.

    Once we ascend from the root element, we're in the epilog state where we can 
    process whitespace, comments, and processor instructions. Anything else is an
    error.

    ## Text

    Text Nodes and Attributes trigger string parsing. All strings are surrounded by
    `>`/`<` or `"`.

    Built in entities include:
    - `&amp;`, '&', `\u0026`
    - `&lt;`, '<', `\u003c`
    - `&gt;`, '>', `\u003e`
    - `&apos;`, '\'', `\u0027`
    - `&quot;`, '"', `\u0022`
    - `&#60;` - decimal character references
    - `&#x3c;` - hex character references

    Legal XML characters:
    - `\u0009`, `\u000a`, `\u000d`
    - `\u0020` - `\ud7ff`,
    - `\ue000` - `\ufffd`
    - `\U00010000` - `\U00010fff`

    Illegal XML characters:
    - `\u0000` - `\u0008`
    - `\u000b` - `\u000c`
    - `\u000e` - `\u001f`
    - `\ud800` - `\udfff`
    - `\ufffe` - `\uffff`

    CDATA may produce text node
    processing instruction may produce PI node

'''