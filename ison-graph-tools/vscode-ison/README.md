# ISON Language Support for VS Code

Syntax highlighting and language support for ISON (Implicit Schema Object Notation) and ISONGraph formats.

## Features

### Syntax Highlighting
- Full syntax highlighting for `.ison` and `.isonl` files
- Node and edge section headers
- Node references (`:type:id`)
- Strings, numbers, booleans
- Comments

### Code Snippets
- `graph` - Create a new graph
- `nodes` - Create a nodes section
- `edges` - Create an edges section
- `ref` - Create a node reference
- `social` - Social network template
- `knowledge` - Knowledge graph template

### Commands
- **ISON: Convert JSON to ISON** - Convert JSON graph to ISON format
- **ISON: Convert ISON to JSON** - Convert ISON to JSON format
- **ISON: Format Document** - Format ISON document
- **ISON: Validate Document** - Validate ISON syntax

### Hover Information
Hover over node references to see type and ID information.

## Syntax Overview

### Graph Header
```ison
graph social
directed
```

### Node Sections
```ison
nodes.person
id name age
alice Alice 30
bob Bob 25
```

### Edge Sections
```ison
edges.KNOWS
source target since
:person:alice :person:bob 2020
```

### Node References
```ison
:type:id
:person:alice
:company:techcorp
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ison.formatOnSave` | `false` | Auto-format on save |
| `ison.validateOnSave` | `true` | Validate on save |
| `ison.indentSize` | `2` | Indentation size |

## Installation

### From VSIX
1. Download the `.vsix` file
2. Open VS Code
3. Press `Ctrl+Shift+P` and select "Extensions: Install from VSIX..."
4. Select the downloaded file

### Build from Source
```bash
cd tools/vscode-ison
npm install
npm run compile
vsce package
```

## Example Files

### Social Network (social.ison)
```ison
graph social
directed

nodes.person
id name role
alice Alice Engineer
bob Bob Designer
carol Carol Manager

nodes.company
id name industry
techcorp TechCorp Technology

edges.KNOWS
source target
:person:alice :person:bob
:person:bob :person:carol

edges.WORKS_AT
source target role
:person:alice :company:techcorp Engineer
:person:bob :company:techcorp Designer
```

### Streaming Format (changes.isonl)
```isonl
+n person dave name=Dave age=28
+n company newcorp name=NewCorp
+e WORKS_AT :person:dave :company:newcorp
-n person temp
~n person alice age=31
```

## Token Efficiency

ISON format provides **68.6% token savings** compared to JSON when used in LLM prompts:

| Format | Tokens | Savings |
|--------|--------|---------|
| JSON | 2,039 | - |
| **ISON** | **639** | **68.6%** |

## Links

- [ISONGraph Documentation](https://github.com/isongraph/isongraph)
- [ISON Format Specification](https://github.com/isongraph/ison-spec)

## License

MIT License
