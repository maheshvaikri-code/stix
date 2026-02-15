# ISONGraph Playground

An interactive web-based tool for converting between JSON and ISON formats, with real-time token counting and validation.

## Features

- **Format Conversion**: Convert between JSON and ISON formats
- **Token Counting**: See estimated token counts for both formats
- **Token Savings**: View percentage savings when using ISON
- **Validation**: Validate ISON syntax
- **Examples**: Load pre-built graph examples
- **Download**: Export graphs in either format

## Usage

### Local Development

1. Open `index.html` in a web browser
2. Or serve with a local server:

```bash
# Python 3
python -m http.server 8000

# Node.js
npx serve
```

3. Navigate to `http://localhost:8000`

### Online

Deploy to any static hosting service:
- GitHub Pages
- Netlify
- Vercel
- Cloudflare Pages

## File Structure

```
playground/
├── index.html      # Main HTML page
├── styles.css      # Styling
├── converter.js    # ISON/JSON conversion logic
├── app.js          # Application logic
└── README.md       # This file
```

## Conversion Examples

### JSON to ISON

Input (JSON):
```json
{
  "name": "social",
  "nodes": [
    {"type": "person", "id": "alice", "name": "Alice", "age": 30}
  ],
  "edges": [
    {"rel_type": "KNOWS", "source": {"type": "person", "id": "alice"}, "target": {"type": "person", "id": "bob"}}
  ]
}
```

Output (ISON):
```
graph social
directed

nodes.person
id name age
alice Alice 30

edges.KNOWS
source target
:person:alice :person:bob
```

### Token Savings

| Format | Example Size | Tokens | Savings |
|--------|-------------|--------|---------|
| JSON | 500 bytes | ~143 | - |
| ISON | 200 bytes | ~57 | 60% |

## API

The `ISONConverter` object provides these methods:

```javascript
// Convert JSON to ISON
const ison = ISONConverter.jsonToIson(jsonObject);

// Convert ISON to JSON
const json = ISONConverter.isonToJson(isonString);

// Validate ISON
const errors = ISONConverter.validate(isonString);

// Estimate tokens
const tokens = ISONConverter.estimateTokens(text);

// Count elements
const { nodeCount, edgeCount } = ISONConverter.countElements(isonString);
```

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License
