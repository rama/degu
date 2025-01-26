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

    def _process_headers(self, headerBytes):
        # decode and discard status line and blank lines
        headerList = headerBytes.decode("utf8").split("\r\n")[1:-2]
        headers = {}
        for header in headerList:
            header = header.split(":")
            headers[header[0]] = header[1]
        print(headers)
        return headers

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
        headers = b""
        while b"\r\n\r\n" not in headers:
            headers += s.recv(1)

        headers = self._process_headers(headers)
        if "Transfer-Encoding" in headers and "chunked" in headers["Transfer-Encoding"]:
            print("THIS IS CHUNKED")
        else:
            print("this is NOT chunked")

        s.close()
        # return content


class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag, parent):
        self.tag = tag
        self.children = []
        self.parent = parent

    def __repr__(self):
        return "<" + self.tag + ">"


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
            elif c == ">":
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
        response = self.load(address)
        tree = HTMLParser(response).parse()
        lines, links = self.get_content(tree)
        page_num = 1
        self.display(lines, page_num)
        while self.status == "RUNNING":
            user_input = input("<link_number>, Back, <RETURN> for more, or Quit: ")
            if user_input == "quit":
                return
            elif user_input == "":
                page_num += 1
                self.display(lines, page_num)

    def load(self, address):
        url = URL(address)
        if self.current:
            self.history.append(self.current)
        self.current = url
        response = url.request()
        return response

    def display(self, lines, page_num):
        start = (page_num - 1) * self.size.lines
        end = min(len(lines), page_num * self.size.lines - 1)
        os.system("cls" if os.name == "nt" else "clear")
        for line in lines[start:end]:
            print(line)

    def back(self):
        self.current = None
        self.load(self.history.pop())

    def get_content(self, tree):
        stack = [tree]
        lines = []
        links = []
        while len(stack) > 0:
            node = stack.pop()
            if isinstance(node, Text):
                line = node.text
                if isinstance(node.parent, Link):
                    links.append(node.parent.href)
                    line += f"[{len(links)}]"
                lines.append(line)
            else:
                for child in node.children:
                    stack.append(child)
        lines.append("[End]")
        return lines, links

    def print_tree(self, node, indent=0):
        print(" " * indent, node)
        for child in node.children:
            self.print_tree(child, indent + 2)


if __name__ == "__main__":
    import sys

    URL(sys.argv[1]).request()
    # Browser().start()
