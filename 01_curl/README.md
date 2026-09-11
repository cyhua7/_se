# mycurl

A curl-like HTTP client tool written in Python.

## Features

- HTTP methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- Custom headers (`-H`)
- Request data (`-d`)
- JSON payload (`--json`)
- File upload (`-T`, `-F`)
- Cookie support (`-b`, `-c`)
- Basic authentication (`-u`)
- Proxy support (`-x`)
- SSL/TLS options (`-k`, `--legacy`)
- Verbose output (`-v`)
- Response header inclusion (`-i`)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# GET request
python -m mycurl https://example.com

# POST with data
python -m mycurl -X POST -d "name=test" https://api.example.com/users

# Custom headers
python -m mycurl -H "Accept: application/json" https://api.example.com/data

# Basic auth
python -m mycurl -u user:pass https://secure.example.com

# Upload file
python -m mycurl -T file.txt https://upload.example.com/files

# JSON body
python -m mycurl --json '{"key":"value"}' -X POST https://api.example.com

# Verbose mode
python -m mycurl -v https://example.com

# Ignore SSL errors
python -m mycurl -k https://self-signed.example.com

# Allow legacy TLS renegotiation (old servers, e.g. EDU systems)
python -m mycurl --legacy https://old-server.example.com
```

## Command-line Options

| Option | Description |
|--------|-------------|
| `-X, --request` | HTTP method (default: GET) |
| `-d, --data` | Send data in POST body |
| `-H, --header` | Add custom header |
| `-b, --cookie` | Send cookies |
| `-u, --user` | Basic auth (user:pass) |
| `-x, --proxy` | Use proxy |
| `-T, --upload-file` | Upload local file |
| `-F, --form` | Upload form field |
| `--json` | Send JSON data |
| `-k, --insecure` | Allow insecure SSL |
| `--legacy` | Allow legacy TLS renegotiation (old servers) |
| `-v, --verbose` | Verbose output |
| `-i, --include` | Include response headers |
| `-o, --output` | Write output to file |
| `-s, --silent` | Silent mode |

## License

MIT
