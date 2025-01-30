import socket
import ssl
import os


class URL:
    def __init__(self, url):
        if not url.endswith(".html") and url[-1] != "/":
            url += "/"
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        self.host, url = url.split("/", 1)
        if ":" in self.host:
            self.host, port = self.host.split(":")
            self.port = int(port)
        elif self.scheme == "https":
            self.port = 443
        else:
            self.port = 80
        if len(url) == 0 or url[0] != "/":
            self.path = "/" + url
        else:
            self.path = url

    def request(self):
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        s.connect((self.host, self.port))

        request = f"GET {self.path} HTTP/1.1\r\n"
        request += f"Host: {self.host}\r\n"
        request += f"Connection: close\r\n"
        request += f"User-Agent: Degu/0.0.1\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))
        buffer = b""
        headers_end = -1
        while headers_end == -1:
            buffer += s.recv(8192)
            headers_end = buffer.find(b"\r\n\r\n")

        headers = self._process_headers(buffer[:headers_end])
        buffer = buffer[headers_end + 4 :]
        if "Transfer-Encoding" in headers and "chunked" in headers["Transfer-Encoding"]:
            response = self._receive_chunked_response(s, buffer)
        elif "Content-Length" in headers:
            response = self._receive_fixed_length_response(
                s, int(headers["Content-Length"]), buffer
            )
        else:
            response = self._receive_until_close(s, buffer)
        s.close()
        return response.decode("utf8")

    def _process_headers(self, headerBytes):
        # decode to utf8 and discard status line
        headerList = headerBytes.decode("utf8").split("\r\n")[1:]
        headers = {}
        for header in headerList:
            header = header.split(":")
            headers[header[0]] = header[1]
        return headers

    def _receive_chunked_response(self, s, buffer):
        response = b""
        while True:
            while b"\r\n" not in buffer:
                buffer += s.recv(8192)
            chunk_size, buffer = buffer.split(b"\r\n", 1)
            chunk_size = int(chunk_size, 16)

            if chunk_size == 0:
                break

            if chunk_size < len(buffer):
                chunk = buffer[:chunk_size]
                buffer = buffer[chunk_size + 2 :]  # +2 for CRLF
            else:
                chunk = buffer
                chunk_size -= len(buffer)

                while chunk_size > 0:
                    buffer = s.recv(min(chunk_size, 8192))
                    chunk += buffer
                    chunk_size -= len(buffer)
                buffer = b""  # reset buffer
                s.recv(2)  # +2 for CRLF
            response += chunk
        return response

    def _receive_fixed_length_response(self, s, length, buffer):
        response = buffer
        remaining = length - len(buffer)
        while remaining > 0:
            buffer = s.recv(min(remaining, 8192))
            response += buffer
            remaining -= len(buffer)
        return response

    def _receive_until_close(self, s, buffer):
        response = buffer
        while True:
            try:
                buffer = s.recv(8192)
                if not buffer:
                    break
                response += buffer
            except:
                break
        return response


class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(f"{self.text[:min(20, len(self.text))]} ...{len(self.text)} chars")


class Element:
    def __init__(self, tag, parent):
        self.tag = tag
        self.children = []
        self.parent = parent

    def __repr__(self):
        return f"<{self.tag}> {self.children[0].text if self.tag == 'span' else ""}"


class Link(Element):
    def __init__(self, tag, parent, href):
        super().__init__(tag, parent)
        # self.id = id
        self.href = href

    def __repr__(self):
        return f"<{self.tag} href={self.href}>"


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]

    def add_text(self, text):
        if text.isspace():
            return
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, text):
        tag = self.get_tag_name(text)
        if tag.startswith("!"):
            return
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            if tag == "a":
                href = self.get_href(text)
                node = Link(tag, parent, href)
            else:
                node = Element(tag, parent)
            self.unfinished.append(node)

    def get_tag_name(self, text):
        parts = text.split()
        return parts[0].casefold()

    def get_href(self, text):
        parts = text.split()
        for attrpair in parts[1:]:
            if "href" in attrpair:
                return attrpair.split("=", 1)[1].replace('"', "")

    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text:
                    self.add_text(text)
                text = ""
            elif in_tag and c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()


class Browser:
    def __init__(self):
        self.size = os.get_terminal_size()
        self.history = []
        self.current = None
        self.status = "INIT"
        self.TAGS_TO_IGNORE = ["head", "script", "style", "form", "svg", "img"]
        self.INLINE_TAGS = [
            "a",
            "abbr",
            "acronym",
            "button",
            "br",
            "big",
            "bdo",
            "b",
            "cite",
            "code",
            "dfn",
            "i",
            "em",
            "img",
            "kbd",
            "label",
            "map",
            "object",
            "output",
            "tt",
            "time",
            "samp",
            "small",
            "span",
            "strong",
            "sub",
            "sup",
        ]
        self.end_of_page = True

    def start(self):
        self.status = "STARTED"
        DEGU = ["(\\___/)", "(='.'=) ,", "(_)-(_)//"]
        mid = (self.size.columns // 2, self.size.lines // 2)
        print("~~DEGU~~")
        for row in range(self.size.lines - 2):
            distance_from_mid = row - mid[1]
            if distance_from_mid in [-1, 0, 1]:
                print((" " * (mid[0] - 5)) + DEGU[distance_from_mid + 1])
            else:
                print("")
        self.run()

    def run(self):
        address = input("Enter website URL: ")
        self.status = "RUNNING"
        self.navigate(address)
        while self.status == "RUNNING":
            user_input = input(
                f"<link_number>, Back, {"<RETURN> for more, " if not self.end_of_page else ""}or Quit: "
            )
            if user_input in ["quit", "q"]:
                return
            elif user_input.isdecimal():
                self.navigate(self.links[int(user_input) - 1])
            elif user_input == "":
                if not self.end_of_page:
                    self.page_num += 1
                self.display()

    def navigate(self, address):
        response = self.load(address)
        tree = HTMLParser(response).parse()
        # self.lines, self.links = self.get_content(tree)
        blocks = self.get_blocks(tree)
        self.blocks_to_lines(blocks)
        self.page_num = 1
        self.display()

    def load(self, address):
        url = URL(address)
        if self.current:
            self.history.append(self.current)
        self.current = url
        response = url.request()
        return response

    def display(self):
        start = (self.page_num - 1) * self.size.lines
        end = min(len(self.lines), self.page_num * self.size.lines - 1)
        if self.lines[end - 1] == "[End]":
            self.end_of_page = True
        else:
            self.end_of_page = False
        os.system("cls" if os.name == "nt" else "clear")
        for line in self.lines[start:end]:
            print(line)

    def back(self):
        self.current = None
        self.load(self.history.pop())

    def get_blocks(self, tree):
        stack = [tree]
        blocks = []
        current_block = []
        while len(stack) > 0:
            node = stack.pop()
            if isinstance(node, Text) or node.tag in self.INLINE_TAGS:
                current_block.append(node)
            else:
                if node.parent and node.parent.tag not in self.INLINE_TAGS:
                    if len(current_block) > 0:
                        blocks.append(reversed(current_block))
                        current_block = []
                if node.tag not in self.TAGS_TO_IGNORE:
                    for child in node.children:
                        stack.append(child)
        blocks.reverse()
        return blocks

    def blocks_to_lines(self, blocks):
        self.lines = []
        self.links = []
        for block in blocks:
            line = ""
            for node in block:
                if isinstance(node, Text):
                    if node.parent.tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                        line += "\n"
                    line += node.text
                else:
                    line += self.recurse_inline_children(node)
            self.lines.append(line)
        self.lines.append("[End]")

    def recurse_inline_children(self, node):
        text = ""
        for child in node.children:
            if isinstance(child, Text):
                text += child.text
                if isinstance(node, Link):
                    self.links.append(node.href)
                    text += f"[{len(self.links)}]"
            else:
                self.recurse_inline_children(child)
        return text

    def get_content(self, tree):
        stack = [tree]
        blocks = []
        links = {}
        link_count = 0
        current_block = ""
        while len(stack) > 0:
            node = stack.pop()
            if isinstance(node, Text):
                if node.parent.tag in self.INLINE_TAGS:
                    current_block += node.text
                else:
                    if node.parent.tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                        current_block = "\n" + node.text
                    else:
                        current_block = node.text
                if isinstance(node.parent, Link):
                    link_count += 1
                    links[link_count] = node.parent.href
                    current_block += f"[{link_count}]"
                blocks.append(current_block)
            else:
                if node.parent and node.parent.tag not in self.INLINE_TAGS:
                    current_block = ""
                if node.tag not in self.TAGS_TO_IGNORE:
                    for child in node.children:
                        stack.append(child)
        blocks.reverse()
        blocks.append("[End]")
        return blocks, links

    def print_tree(self, node, indent=0):
        print(" " * indent, node)
        for child in node.children:
            self.print_tree(child, indent + 4)


if __name__ == "__main__":
    # import sys

    # URL(sys.argv[1]).request()
    Browser().start()
