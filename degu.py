import socket
import ssl


class URL:
    def __init__(self, url):
        if url[-1] != "/":
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

    def show(self, body):
        in_tag = False
        entities = {"lt": "<", "gt": ">,"}
        is_entity = False
        current_entity = ""
        for c in body:
            if c == "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif c == "&":
                is_entity = True
            elif is_entity and c == ";":
                print("{current_entity=}")
                current_entity = ""
                is_entity = False
            elif is_entity:
                current_entity += c
            elif not in_tag and not is_entity:
                print(c, end="")


def load(url):
    body = url.request()
    url.show(body)


if __name__ == "__main__":
    import sys

    load(URL(sys.argv[1]))
