# MikroTik HotSpot Voucher Tester

Python command-line tools for testing MikroTik HotSpot voucher login pages and generating voucher batches.

This repository currently contains:

- `mikrotik_jsmd5_loginv2.py`: tests MikroTik HotSpot logins that use the JavaScript MD5 / CHAP flow
- `llm_debug.py`: optional OpenAI-based failure analysis for saved logs or failed login attempts
- `Voucher-generator/vgen.py`: standalone voucher generator for batch creation

## Scope

The tester is designed for captive portals that behave like standard MikroTik login pages:

- fetch the login form
- extract the form action and challenge data
- calculate the MD5 response for CHAP-based login
- fall back to PAP if CHAP data is not available
- evaluate the result using redirect history, response content, and final URL

Portal templates vary. This tool works best when the target login page still follows common MikroTik field names and request flow.

## Features

- Single voucher testing
- Wordlist-based testing
- CHAP challenge extraction from JavaScript and hidden form fields
- PAP fallback when CHAP is unavailable
- Verbose request and response logging
- Summary report output
- Optional AI-assisted analysis for failed attempts or saved HTML / log files

## Requirements

- Python 3.8 or newer
- `requests` for the tester
- `openai` only if you want to use the optional LLM analysis mode

Install everything with:

```bash
pip install -r requirements.txt
```

If you do not need the LLM feature, this is enough:

```bash
pip install requests
```

## Usage

### Test a single voucher

```bash
python mikrotik_jsmd5_loginv2.py -u http://192.168.88.1 --voucher TEST123
```

### Test a wordlist

```bash
python mikrotik_jsmd5_loginv2.py -u http://192.168.88.1 -w vouchers.txt -o report.txt
```

### Verbose mode

```bash
python mikrotik_jsmd5_loginv2.py -u hotspot.local -w vouchers.txt -v
```

### Analyze the last failed attempt with OpenAI

Set `OPENAI_API_KEY` first, then run:

```bash
python mikrotik_jsmd5_loginv2.py -u hotspot.local -w vouchers.txt -v --llm-debug
```

### Analyze a saved file with OpenAI

```bash
python mikrotik_jsmd5_loginv2.py --analyze-file failed_login.html
```

## Main Options

- `-u, --url`: target portal URL or hostname
- `--voucher`: test a single voucher
- `-w, --wordlist`: test multiple vouchers from a file
- `-t, --timeout`: HTTP timeout in seconds
- `-d, --delay`: delay between attempts
- `-o, --output`: save the summary report to a file
- `-v, --verbose`: print detailed request and response information
- `--no-progress`: disable the progress display
- `--llm-debug`: send the last failed attempt to the optional LLM analyzer
- `--analyze-file`: analyze a saved HTML or log file with the optional LLM analyzer
- `--analyze-model`: choose the OpenAI model used by the analyzer

Run `python mikrotik_jsmd5_loginv2.py --help` for the full CLI reference.

## Notes on the LLM Analyzer

The AI-assisted debug mode is optional and off by default.

- it requires the `openai` package
- it requires `OPENAI_API_KEY`
- it masks voucher and request values before building the analysis payload
- it does not change the voucher testing flow; it only adds diagnosis after a failed run or for a saved file

## Voucher Generator

The repository also includes a separate generator in `Voucher-generator/vgen.py`.

Use it if you need to create batch voucher data for lab or operational workflows. It is independent from the tester.

## Limitations

- success detection is heuristic, not authoritative
- some portals use custom JavaScript or non-standard field names
- some captive portals require additional cookies or intermediate redirects
- the LLM analyzer can help narrow down failures, but it cannot replace packet capture or direct router-side inspection

## Legal and Ethical Use

Use this tool only on systems you own or are explicitly authorized to test.

Do not use it against third-party networks, captive portals, or customer infrastructure without written permission.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).
