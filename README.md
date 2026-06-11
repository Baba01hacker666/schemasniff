# SchemaSniff

![SchemaSniff](https://img.shields.io/badge/Made%20by-baba01hacker-blue)
![Python](https://img.shields.io/badge/Python-3.6%2B-green)

**SchemaSniff** is an advanced GraphQL schema reconstructor designed for security researchers, bug bounty hunters, and penetration testers. It reconstructs GraphQL schemas even when introspection is completely disabled by utilizing intelligent field bruteforcing and error message analysis.

Made by **baba01hacker**.

## Features
- **Introspection Bypass:** Works perfectly on endpoints with introspection disabled.
- **Smart Error Analysis:** Deeply inspects error messages to distinguish between field absence, missing arguments, authentication errors, and subfield requirements.
- **Auto-Discovery:** Automatically follows "did you mean" suggestions to discover fields not even in your wordlist.
- **Nested Error Handling:** Parses complex, nested GraphQL error objects (supports Apollo, Hasura, etc.).

## Installation

You can install SchemaSniff directly via pip:

```bash
pip install schemasniff
```

Or from source:

```bash
git clone https://github.com/Baba01hacker666/schemasniff.git
cd schemasniff
pip install .
```

## Usage

```bash
schemasniff -u <url> -w <wordlist> [options]
```

### Options
- `-u`, `--url`: Target GraphQL endpoint URL (required)
- `-w`, `--wordlist`: Wordlist for field bruteforcing (required)
- `-m`, `--method`: HTTP Method (GET or POST, default is POST)
- `--headers`: Custom headers in Key:Value format (e.g., `--headers "Authorization: Bearer token"`)

### Example
```bash
schemasniff -u https://api.target.com/graphql -w ./wordlists/graphql.txt --headers "Authorization: Bearer mytoken"
```

## Disclaimer
This tool is for educational purposes and authorized security testing only. The author is not responsible for any misuse.
