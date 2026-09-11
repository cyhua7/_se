"""Command-line interface for mycurl."""

import json
import sys

import click

from .client import MyCurlClient, RequestConfig


def _safe_print(text: str) -> None:
    """Print text without crashing on characters the terminal cannot encode."""
    import sys

    try:
        encoding = sys.stdout.encoding or "utf-8"
    except Exception:
        encoding = "utf-8"
    text = text.encode(encoding, errors="replace").decode(encoding)
    click.echo(text)


@click.command()
@click.argument("url")
@click.option("-X", "--request", "method", default="GET", help="HTTP method to use.")
@click.option("-d", "--data", "data", help="Send data in POST body.")
@click.option("-H", "--header", "headers", multiple=True, help="Add custom header (Key: Value).")
@click.option("-b", "--cookie", "cookie_args", multiple=True, help="Send cookies (Name=Value) or load from file.")
@click.option("-c", "--cookie-jar", "cookie_jar", help="Save cookies to file.")
@click.option("-x", "--proxy", "proxy", help="Use proxy (protocol://host:port).")
@click.option("-u", "--user", "auth", help="Basic auth (user:password).")
@click.option("-A", "--user-agent", "user_agent", help="Set User-Agent header.")
@click.option("-o", "--output", "output_file", help="Write output to file.")
@click.option("-O", "--remote-name", "remote_name", is_flag=True, help="Save with remote filename.")
@click.option("-k", "--insecure", is_flag=True, help="Allow insecure SSL connections.")
@click.option("--legacy", is_flag=True, help="Allow legacy TLS renegotiation (old servers).")
@click.option("-L", "--location", "follow_redirects", is_flag=True, default=False, help="Follow redirects.")
@click.option("--max-redirs", default=10, help="Maximum number of redirects.")
@click.option("--connect-timeout", default=30, help="Connection timeout in seconds.")
@click.option("-T", "--upload-file", "upload_file", help="Upload local file.")
@click.option("-F", "--form", "form_fields", multiple=True, help="Upload form field (name=value or name=@file).")
@click.option("--json", "json_data", help="Send JSON data.")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output.")
@click.option("-i", "--include", "include_headers", is_flag=True, help="Include response headers.")
@click.option("-I", "--head", "head_request", is_flag=True, help="Fetch headers only.")
@click.option("-s", "--silent", is_flag=True, help="Silent mode.")
@click.option("-w", "--write-out", "write_out", help="Output format string.")
@click.version_option(version="0.1.0", prog_name="mycurl")
def main(
    url: str,
    method: str,
    data: str | None,
    headers: tuple[str, ...],
    cookie_args: tuple[str, ...],
    cookie_jar: str | None,
    proxy: str | None,
    auth: str | None,
    user_agent: str | None,
    output_file: str | None,
    remote_name: bool,
    insecure: bool,
    legacy: bool,
    follow_redirects: bool,
    max_redirs: int,
    connect_timeout: int,
    upload_file: str | None,
    form_fields: tuple[str, ...],
    json_data: str | None,
    verbose: bool,
    include_headers: bool,
    head_request: bool,
    silent: bool,
    write_out: str | None,
) -> None:
    """mycurl - A curl-like HTTP client tool.

    \b
    Examples:
        mycurl https://example.com
        mycurl -X POST -d "name=test" https://api.example.com/users
        mycurl -H "Accept: application/json" https://api.example.com/data
        mycurl -u user:pass https://secure.example.com
        mycurl -k https://self-signed.example.com
        mycurl -T file.txt https://upload.example.com/files
    """
    parsed_headers = {}
    for h in headers:
        key, _, value = h.partition(":")
        parsed_headers[key.strip()] = value.strip()

    cookies = {}
    cookie_file = None
    for c in cookie_args:
        if "=" in c:
            key, _, value = c.partition("=")
            cookies[key.strip()] = value.strip()
        else:
            cookie_file = c
            cookies = {}
            break

    parsed_json = None
    if json_data:
        try:
            parsed_json = json.loads(json_data)
        except json.JSONDecodeError:
            click.echo(f"Error: Invalid JSON data: {json_data}", err=True)
            sys.exit(1)

    upload_field = None
    upload_path = upload_file
    if form_fields:
        for field_str in form_fields:
            field_name, _, field_value = field_str.partition("=")
            if field_value.startswith("@"):
                upload_path = field_value[1:]
                upload_field = field_name
                break

    if head_request:
        method = "HEAD"

    config = RequestConfig(
        url=url,
        method=method,
        headers=parsed_headers,
        data=data,
        json_data=parsed_json,
        cookies=cookies,
        cookie_file=cookie_file,
        proxy=proxy,
        timeout=connect_timeout,
        verify_ssl=not insecure,
        follow_redirects=follow_redirects,
        max_redirects=max_redirs,
        upload_file=upload_path,
        upload_field=upload_field or "file",
        verbose=verbose,
        include_headers=include_headers,
        user_agent=user_agent,
        auth=auth,
        insecure=insecure,
        legacy=legacy,
    )

    client = MyCurlClient(config)

    try:
        response = client.execute()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not silent:
        if include_headers:
            for key, value in response.headers.items():
                click.echo(f"{key}: {value}")
            click.echo("")

        _safe_print(response.body)

    if write_out:
        output = write_out
        output = output.replace("%{http_code}", str(response.status_code))
        output = output.replace("%{url_effective}", response.url)
        output = output.replace("%{time_total}", f"{response.elapsed_ms:.3f}")
        click.echo(output)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.body)
    elif remote_name:
        from urllib.parse import urlparse

        filename = urlparse(response.url).path.split("/")[-1]
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(response.body)

    if response.status_code >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
