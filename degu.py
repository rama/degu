import socket
import ssl


class URL:
    def __init__(self, url):
        if not url.endswith(".html") and url[-1] != "/":
            url += "/"
        self.scheme, url = url.split("://", 1)
        if self.scheme not in ["http", "https"]:
            print("Unsupported protocol")
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
        print(self.scheme, self.host, self.port, self.path)

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
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        print(version, status, explanation)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        content = response.read()
        s.close()
        return content


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
        import os

        self.size = os.get_terminal_size()
        self.history = []
        self.current = None

    def start(self):
        DEGU = ["(\___/)", "(='.'=) ,", "(_)-(_)//"]
        mid = (self.size.columns // 2, self.size.lines // 2)
        print("~~DEGU~~")
        for row in range(self.size.lines - 2):
            distance_from_mid = row - mid[1]
            if distance_from_mid in [-1, 0, 1]:
                print((" " * (mid[0] - 5)) + DEGU[distance_from_mid + 1])
            else:
                print("")

        address = input("Enter website URL: ")
        self.load(URL(address))

    def load(self, url):
        if self.current:
            self.history.append(self.current)
        self.current = url
        tree = HTMLParser(url.request()).parse()
        self.display(tree)

    def back(self):
        self.current = None
        self.load(self.history.pop())

    def display(self, tree):
        if isinstance(tree, Text):
            print(tree.text)
            if isinstance(tree.parent, Link):
                print(tree.parent.href)
        else:
            for child in tree.children:
                self.display(child)

    def print_tree(self, node, indent=0):
        print(" " * indent, node)
        for child in node.children:
            self.print_tree(child, indent + 2)


if __name__ == "__main__":
    import sys

    Browser().start()
