# ANP Protocol Authentication Communication Example

[中文版](README.md)

This is a DID WBA method example implemented using FastAPI and Agent_Connect library, supporting both client and server functionality.

## Features

### resp (Server-side) Features
- ANP protocol authentication: DID WBA initial authentication, Bearer Token session authentication
- ANP natural language communication: via the `/wba/anp-nlp` interface

### req (Client-side) Features
- Automatically generates DID and keys or loads existing identities
- Initiates initial authentication and token requests to resp
- Sends messages to the anp-nlp interface of resp

## Installation

### Environment Setup

1. Clone the project
2. Create an environment configuration file
   ```
   cp .env.example .env
   ```
3. Edit the .env file to set the necessary configuration items

### Install Dependencies with Poetry

```bash
# Activate virtual environment (if exists)
source .venv/bin/activate

# Install dependencies
poetry install
```

## Running Methods

This project provides three different running methods:

### 1. Direct ANP Interface Calls

Run `anp_llmapp.py` to directly call the ANP interfaces in `anp_core`:

```bash
python anp_llmapp.py
```

### 2. MCP Interface Calls via stdio

Run `mcp_stdio_client.py` to call the ANP interfaces wrapped by `mcp_stdio_server.py` via stdio, which can debug the complete MCP process:

```bash
# Start the server
python -m anp_mcpwrapper.mcp_stdio_server

# Start the client
python -m anp_mcpwrapper.mcp_stdio_client
```

### 3. SSE Interface Calls

Start `mcp_stdio_server.py` as an SSE service and call it via the SSE interface:

```bash
python -m anp_mcpwrapper.mcp_stdio_server -t sse
```

**Note**: Methods 2 and 3 have been successfully configured and tested in the TRAE environment.

## Project Structure

```
.
├── anp_core/            # Encapsulated ANP interfaces for developers
├── anp_mcpwrapper/      # MCP interface implementation
├── api/                 # API routing module
├── core/                # Application framework
├── doc/                 # Documentation and test keys
├── examples/            # More examples for developers in the future
├── utils/               # Utility functions
├── logs/                # Log files
├── setup/               # Installation solutions (currently unused)
├── anp_llmapp.py        # Application directly calling ANP interfaces
└── anp_llmagent.py      # Planned to be developed as an out-of-the-box agent
```

## Project Description

1. **anp_core**: Encapsulated ANP interfaces for developers, currently DID authentication is for local testing, the next version will add practical DID services

2. **anp_mcpwrapper**: Implements MCP interface integration, currently tested successfully in the TRAE environment, not successful in the Claude environment

3. **api/core**: Application framework, providing API routing and core configuration

4. **doc**: Documentation and test keys

5. **examples**: More examples for developers will be added in the future

6. **utils/logs**: Utility functions and log files

7. **setup**: Installation solutions will be added later, currently unused

8. **anp_llmagent.py**: Planned to be developed as an out-of-the-box agent, interoperable with `anp_llmapp.py`/MCP calls

## API Endpoints

- `GET /agents/example/ad.json`: Get agent description information
- `GET /ad.json`: Get advertisement JSON data, requires authentication
- `POST /auth/did-wba`: DID WBA initial authentication
- `GET /auth/verify`: Verify Bearer Token
- `GET /wba/test`: Test DID WBA authentication
- `POST /wba/anp-nlp`: ANP natural language communication interface
- `GET /wba/user/{user_id}/did.json`: Get user DID document
- `PUT /wba/user/{user_id}/did.json`: Save user DID document

## Workflow

### Server Workflow
1. Start the server and listen for requests
2. Receive DID WBA authentication requests and verify signatures
3. Generate and return access tokens
4. Process subsequent requests using tokens

### Client Workflow
1. Generate or load DID documents and private keys
2. Send requests to the server with DID WBA signature headers
3. Receive and save tokens
4. Use tokens for subsequent requests

## Authentication Details

The example implements two authentication methods:

1. **Initial DID WBA Authentication**: Signature verification according to DID WBA specification
2. **Bearer Token Authentication**: JWT token for subsequent request authentication

For detailed authentication processes, refer to the code implementation and [DID WBA Specification](https://github.com/agent-network-protocol/AgentNetworkProtocol/blob/main/chinese/03-did%3Awba%E6%96%B9%E6%B3%95%E8%A7%84%E8%8C%83.md)
